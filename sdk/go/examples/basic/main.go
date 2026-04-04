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

	// Generate random hex string (256 bits)
	hex, err := client.GenerateHex(256)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Hex:", hex)

	// Generate random integer in [1, 100]
	n, err := client.GenerateInt(1, 100)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Integer:", n)

	// Generate random float in [0.0, 1.0)
	f, err := client.GenerateFloat()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Float: %.15f\n", f)

	// Generate 32 random bytes
	b, err := client.GenerateBytes(32)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Bytes: %x\n", b)

	// Generate a UUID
	uuid, err := client.GenerateUUID()
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("UUID:", uuid)

	// Generate a 256-bit cryptographic key
	key, err := client.GenerateKey(256)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Key:", key.KeyHex)
	fmt.Println("Source:", key.Source)
}
