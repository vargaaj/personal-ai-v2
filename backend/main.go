package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"

	openrouter "github.com/OpenRouterTeam/go-sdk"
	"github.com/OpenRouterTeam/go-sdk/models/components"
	"github.com/joho/godotenv"
)

func main() {

	// Load the local openrouter api key
	if err := godotenv.Load(".env.local"); err != nil {
		log.Println("no .env.local found; using system environment")
	}

	// mux is a multiplexer - handles routing for the server
	mux := http.NewServeMux()

	mux.HandleFunc("GET /", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		fmt.Fprint(w, "Hello world")
	})

	http.ListenAndServe(":8081", mux)

	// Add POST /api/chat here.
	client := openrouter.New(
		openrouter.WithSecurity(os.Getenv("OPENROUTER_API_KEY")),
	)

	// Simple setup for sending a message to the llm
	response, err := client.Chat.Send(
		context.Background(),
		components.ChatRequest{
			// Selecting any of the free models
			Model: openrouter.Pointer("openrouter/free"),
			Messages: []components.ChatMessages{
				components.CreateChatMessagesUser(
					components.ChatUserMessage{
						// Selecting the user role
						Role: components.ChatUserMessageRoleUser,
						// Actual content of the message
						Content: components.CreateChatUserMessageContentStr(
							"Say hello in one short sentence.",
						),
					},
				),
			},
		},
		nil,
	)
	if err != nil {
		log.Fatal(err)
	}

	if response == nil || response.ChatResult == nil {
		log.Fatal("OpenRouter returned no chat result")
	}

	if len(response.ChatResult.Choices) == 0 {
		log.Fatal("OpenRouter returned no choices")
	}

	content, ok := response.ChatResult.Choices[0].Message.Content.GetOrZero()
	if !ok || content.Str == nil {
		log.Fatal("OpenRouter returned no text content")
	}

	fmt.Println("Model used:", response.ChatResult.Model)
	fmt.Println("Response:", *content.Str)

}
