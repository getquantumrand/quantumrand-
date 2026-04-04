package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"

	quantumrand "github.com/getquantumrand/quantumrand-go"
)

func main() {
	apiKey := os.Getenv("QUANTUMRAND_API_KEY")
	if apiKey == "" {
		log.Fatal("Set QUANTUMRAND_API_KEY environment variable")
	}

	client := quantumrand.NewClient(apiKey)

	// Generate a quantum transaction ID
	tx, err := client.Finance.CreateTxID()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Transaction ID:", tx.TxID)
	fmt.Println("Source:", tx.EntropySource)
	fmt.Println("Pool healthy:", tx.PoolHealthy)

	// Generate a 6-digit OTP
	otp, err := client.Finance.CreateOTP(6)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("\nOTP:", otp.OTP)
	fmt.Println("Expires:", otp.ExpiresAt)

	// Generate a replay-prevention nonce
	nonce, err := client.Finance.CreateNonce()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("\nNonce:", nonce.Nonce[:32], "...")
	fmt.Println("Single use:", nonce.SingleUse)

	// Generate an Ed25519 signing keypair
	kp, err := client.Finance.CreateKeypair()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("\nKeypair ID:", kp.KeypairID)
	fmt.Println("Algorithm:", kp.Algorithm)
	fmt.Println("Public key:", kp.PublicKey)

	// Sign an audit payload
	payload := `{"action":"wire_transfer","amount":50000,"currency":"USD"}`
	sig, err := client.Finance.AuditSign(payload)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("\nSignature:", sig.Signature[:32], "...")
	fmt.Println("Payload hash:", sig.PayloadHash[:32], "...")
	fmt.Println("Algorithm:", sig.Algorithm)

	// Pretty-print the full signature response
	b, _ := json.MarshalIndent(sig, "", "  ")
	fmt.Println("\nFull response:")
	fmt.Println(string(b))
}
