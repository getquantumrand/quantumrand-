package quantumrand

import (
	"net/url"
	"strconv"
)

// AuditService provides access to audit log and compliance endpoints.
type AuditService struct {
	client *Client
}

func auditQuery(opts *AuditLogOptions) url.Values {
	q := url.Values{}
	if opts == nil {
		return q
	}
	if opts.Endpoint != "" {
		q.Set("endpoint", opts.Endpoint)
	}
	if opts.DateFrom != "" {
		q.Set("date_from", opts.DateFrom)
	}
	if opts.DateTo != "" {
		q.Set("date_to", opts.DateTo)
	}
	if opts.Limit > 0 {
		q.Set("limit", strconv.Itoa(opts.Limit))
	}
	if opts.Offset > 0 {
		q.Set("offset", strconv.Itoa(opts.Offset))
	}
	return q
}

// Logs retrieves paginated audit logs for the authenticated API key.
// Pass nil for opts to use defaults (100 entries, offset 0).
func (a *AuditService) Logs(opts *AuditLogOptions) (*AuditLogResponse, error) {
	var r AuditLogResponse
	err := a.client.request("GET", "/v1/audit/logs", auditQuery(opts), nil, &r)
	return &r, err
}

// Summary returns aggregate usage stats for the authenticated API key.
func (a *AuditService) Summary() (*AuditSummaryResponse, error) {
	var r AuditSummaryResponse
	err := a.client.request("GET", "/v1/audit/summary", nil, nil, &r)
	return &r, err
}

// Export downloads audit logs as raw CSV bytes.
// Pass nil for opts to export all logs.
func (a *AuditService) Export(opts *AuditLogOptions) ([]byte, error) {
	q := url.Values{}
	if opts != nil {
		if opts.Endpoint != "" {
			q.Set("endpoint", opts.Endpoint)
		}
		if opts.DateFrom != "" {
			q.Set("date_from", opts.DateFrom)
		}
		if opts.DateTo != "" {
			q.Set("date_to", opts.DateTo)
		}
	}
	return a.client.requestRaw("GET", "/v1/audit/export", q)
}
