"""Stripe billing: checkout sessions, webhooks, subscription management."""

import logging
import stripe
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field

from app.config import (
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_ENABLED,
    STRIPE_PRICE_INDIE, STRIPE_PRICE_STARTUP, STRIPE_PRICE_BUSINESS,
)
from app.database import (
    update_user_stripe, update_user_tier, get_user_by_stripe_customer,
    _users_col,
)

logger = logging.getLogger("quantumrand")

router = APIRouter(prefix="/billing", tags=["Billing"], include_in_schema=False)

if STRIPE_ENABLED:
    stripe.api_key = STRIPE_SECRET_KEY

GRACE_PERIOD_DAYS = 3

TIER_PRICES = {
    "indie": STRIPE_PRICE_INDIE,
    "startup": STRIPE_PRICE_STARTUP,
    "business": STRIPE_PRICE_BUSINESS,
}

PRICE_TO_TIER = {}
if STRIPE_PRICE_INDIE:
    PRICE_TO_TIER[STRIPE_PRICE_INDIE] = "indie"
if STRIPE_PRICE_STARTUP:
    PRICE_TO_TIER[STRIPE_PRICE_STARTUP] = "startup"
if STRIPE_PRICE_BUSINESS:
    PRICE_TO_TIER[STRIPE_PRICE_BUSINESS] = "business"


class CheckoutRequest(BaseModel):
    tier: str = Field(..., description="Target tier: indie, startup, or business")


@router.post("/checkout")
def create_checkout(body: CheckoutRequest, request: Request):
    """Create a Stripe Checkout session for upgrading to a paid tier."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    from app.user_auth import get_current_user
    user = get_current_user(request)

    tier = body.tier.lower()
    if tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Choose: indie, startup, business")

    price_id = TIER_PRICES[tier]
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Price not configured for {tier} tier")

    # Get or create Stripe customer
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=user["email"],
            metadata={"user_id": user["user_id"]},
        )
        customer_id = customer.id
        update_user_stripe(user["user_id"], customer_id)

    # If user already has a subscription, redirect to portal instead
    sub_id = user.get("stripe_subscription_id")
    if sub_id:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            if sub.status in ("active", "trialing"):
                portal = stripe.billing_portal.Session.create(
                    customer=customer_id,
                    return_url="https://quantumrand.dev/dashboard",
                )
                return {"success": True, "data": {"url": portal.url, "type": "portal"}}
        except stripe.error.InvalidRequestError:
            pass

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://quantumrand.dev/dashboard?billing=success",
        cancel_url="https://quantumrand.dev/dashboard?billing=cancelled",
        metadata={"user_id": user["user_id"], "tier": tier},
    )

    return {"success": True, "data": {"url": session.url, "session_id": session.id}}


@router.post("/portal")
def create_portal(request: Request):
    """Create a Stripe Customer Portal session for managing subscription."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    from app.user_auth import get_current_user
    user = get_current_user(request)

    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account found. Subscribe to a paid plan first.")

    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url="https://quantumrand.dev/dashboard",
    )

    return {"success": True, "data": {"url": portal.url}}


@router.get("/status")
def billing_status(request: Request):
    """Get current billing status for the authenticated user."""
    from app.user_auth import get_current_user
    user = get_current_user(request)

    tier = user.get("tier", "free")
    sub_id = user.get("stripe_subscription_id", "")
    status = "none"
    current_period_end = None
    cancel_at_period_end = False
    grace_until = user.get("grace_until", "")
    in_grace = False

    if grace_until:
        try:
            grace_dt = datetime.fromisoformat(grace_until)
            in_grace = datetime.now(timezone.utc) < grace_dt
        except (ValueError, TypeError):
            pass

    if sub_id and STRIPE_ENABLED:
        try:
            sub = stripe.Subscription.retrieve(sub_id)
            status = sub.status
            current_period_end = sub.current_period_end
            cancel_at_period_end = sub.cancel_at_period_end
        except Exception:
            status = "error"

    return {
        "success": True,
        "data": {
            "tier": tier,
            "subscription_status": status,
            "current_period_end": current_period_end,
            "cancel_at_period_end": cancel_at_period_end,
            "has_billing": bool(user.get("stripe_customer_id")),
            "in_grace_period": in_grace,
            "grace_until": grace_until if in_grace else None,
        },
    }


@router.post("/cancel")
def cancel_subscription(request: Request):
    """Cancel subscription immediately, downgrade to free."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    from app.user_auth import get_current_user
    user = get_current_user(request)

    sub_id = user.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    try:
        stripe.Subscription.cancel(sub_id)
    except Exception as e:
        logger.error(f"Stripe cancel error: {e}")
        raise HTTPException(status_code=502, detail="Could not cancel subscription")

    update_user_tier(user["user_id"], "free")
    _users_col.document(user["user_id"]).update({
        "stripe_subscription_id": "",
        "grace_until": "",
    })

    return {"success": True, "data": {"message": "Subscription cancelled. Downgraded to free tier."}}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_ENABLED:
        raise HTTPException(status_code=503, detail="Billing not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data)
    elif event_type == "invoice.payment_succeeded":
        _handle_payment_succeeded(data)

    return {"received": True}


def _handle_checkout_completed(session):
    """Checkout completed — activate subscription and upgrade tier."""
    customer_id = session.get("customer")
    sub_id = session.get("subscription")
    tier = session.get("metadata", {}).get("tier", "")
    user_id = session.get("metadata", {}).get("user_id", "")

    if not tier or not user_id:
        logger.warning(f"Checkout missing metadata: tier={tier}, user_id={user_id}")
        return

    update_user_stripe(user_id, customer_id, sub_id)
    update_user_tier(user_id, tier)
    # Clear any grace period from previous failed payments
    _users_col.document(user_id).update({"grace_until": ""})
    logger.info(f"User {user_id} upgraded to {tier} via checkout")


def _handle_subscription_updated(subscription):
    """Subscription changed — update tier based on current price."""
    customer_id = subscription.get("customer")
    user = get_user_by_stripe_customer(customer_id)
    if not user:
        return

    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        new_tier = PRICE_TO_TIER.get(price_id, "")
        if new_tier:
            update_user_tier(user["user_id"], new_tier)
            _users_col.document(user["user_id"]).update({
                "stripe_subscription_id": subscription["id"],
                "grace_until": "",
            })
            logger.info(f"User {user['user_id']} subscription updated to {new_tier}")


def _handle_subscription_deleted(subscription):
    """Subscription cancelled — downgrade to free."""
    customer_id = subscription.get("customer")
    user = get_user_by_stripe_customer(customer_id)
    if not user:
        return

    update_user_tier(user["user_id"], "free")
    _users_col.document(user["user_id"]).update({
        "stripe_subscription_id": "",
        "grace_until": "",
    })
    logger.info(f"User {user['user_id']} subscription deleted, downgraded to free")


def _handle_payment_failed(invoice):
    """Payment failed — start 3-day grace period, then downgrade to free."""
    customer_id = invoice.get("customer")
    user = get_user_by_stripe_customer(customer_id)
    if not user:
        logger.warning(f"Payment failed for unknown customer {customer_id}")
        return

    # Only set grace period if user is on a paid tier and not already in grace
    tier = user.get("tier", "free")
    if tier == "free":
        return

    existing_grace = user.get("grace_until", "")
    if existing_grace:
        # Already in grace period — check if it expired
        try:
            grace_dt = datetime.fromisoformat(existing_grace)
            if datetime.now(timezone.utc) >= grace_dt:
                # Grace period expired — downgrade now
                update_user_tier(user["user_id"], "free")
                _users_col.document(user["user_id"]).update({
                    "stripe_subscription_id": "",
                    "grace_until": "",
                })
                logger.warning(f"User {user['user_id']} grace period expired, downgraded to free")
                return
        except (ValueError, TypeError):
            pass
        logger.warning(f"Payment failed again for user {user['user_id']}, grace period still active")
        return

    # Start grace period
    grace_until = (datetime.now(timezone.utc) + timedelta(days=GRACE_PERIOD_DAYS)).isoformat()
    _users_col.document(user["user_id"]).update({"grace_until": grace_until})
    logger.warning(f"Payment failed for user {user['user_id']} ({tier}), grace period until {grace_until}")


def _handle_payment_succeeded(invoice):
    """Payment succeeded — clear any grace period."""
    customer_id = invoice.get("customer")
    user = get_user_by_stripe_customer(customer_id)
    if not user:
        return

    if user.get("grace_until"):
        _users_col.document(user["user_id"]).update({"grace_until": ""})
        logger.info(f"User {user['user_id']} payment succeeded, grace period cleared")
