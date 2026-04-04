package main

import (
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

	// Get audit summary
	summary, err := client.Audit.Summary()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Calls today: %d\n", summary.TotalCallsToday)
	fmt.Printf("Calls this month: %d\n", summary.TotalCallsThisMonth)
	fmt.Printf("Most used: %s\n", summary.MostUsedEndpoint)
	fmt.Printf("Avg latency: %.2fms\n", summary.AvgResponseTimeMs)
	fmt.Printf("Quantum %%: %.1f%%\n", summary.QuantumPercentage)

	// Get recent audit logs
	logs, err := client.Audit.Logs(&quantumrand.AuditLogOptions{
		Limit: 10,
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("\nRecent logs (%d entries):\n", logs.Count)
	for _, entry := range logs.Logs {
		fmt.Printf("  [%s] %s — %s — %.1fms\n",
			entry.CreatedAt[:19], entry.Endpoint, entry.EntropySource, entry.ResponseTimeMs)
	}

	// Export logs as CSV
	csv, err := client.Audit.Export(nil)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("\nCSV export (%d bytes):\n", len(csv))
	// Print first 200 chars
	preview := string(csv)
	if len(preview) > 200 {
		preview = preview[:200] + "..."
	}
	fmt.Println(preview)

	// Check entropy pool health
	pool, err := client.Health.Pool()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("\nEntropy pool: %d/%d bits (healthy: %v)\n",
		pool.PoolDepth, pool.PoolTarget, pool.PoolHealthy)
	fmt.Printf("Source: %s | IBM: %s | Refills: %d\n",
		pool.EntropySource, pool.IBMQueueStatus, pool.RefillCount)
}
