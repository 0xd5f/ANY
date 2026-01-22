package main

import (
	"context"
	"crypto/subtle"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

const (
	listenAddr     = "127.0.0.1:28262"
	mongoURI       = "mongodb://localhost:27017"
	dbName         = "blitz_panel"
	collectionName = "users"
)

type User struct {
	ID                  string `bson:"_id"`
	Password            string `bson:"password"`
	MaxDownloadBytes    int64  `bson:"max_download_bytes"`
	ExpirationDays      int    `bson:"expiration_days"`
	AccountCreationDate string `bson:"account_creation_date"`
	Blocked             bool   `bson:"blocked"`
	UploadBytes         int64  `bson:"upload_bytes"`
	DownloadBytes       int64  `bson:"download_bytes"`
	UnlimitedUser       bool   `bson:"unlimited_user"`
}

type httpAuthRequest struct {
	Addr string `json:"addr"`
	Auth string `json:"auth"`
	Tx   uint64 `json:"tx"`
}

type httpAuthResponse struct {
	OK bool   `json:"ok"`
	ID string `json:"id"`
}

var userCollection *mongo.Collection

func authHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req httpAuthRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	username, password, ok := strings.Cut(req.Auth, ":")
	if !ok {
		json.NewEncoder(w).Encode(httpAuthResponse{OK: false})
		return
	}

	var user User
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := userCollection.FindOne(ctx, bson.M{"_id": username}).Decode(&user)
	if err != nil {
		json.NewEncoder(w).Encode(httpAuthResponse{OK: false})
		return
	}

	if user.Blocked {
		json.NewEncoder(w).Encode(httpAuthResponse{OK: false})
		return
	}

	if subtle.ConstantTimeCompare([]byte(user.Password), []byte(password)) != 1 {
		time.Sleep(5 * time.Second)
		json.NewEncoder(w).Encode(httpAuthResponse{OK: false})
		return
	}

	if user.UnlimitedUser {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(httpAuthResponse{OK: true, ID: username})
		return
	}

	if user.ExpirationDays > 0 {
		creationDate, err := time.Parse("2006-01-02", user.AccountCreationDate)
		if err == nil && time.Now().After(creationDate.AddDate(0, 0, user.ExpirationDays)) {
			json.NewEncoder(w).Encode(httpAuthResponse{OK: false})
			return
		}
	}

	if user.MaxDownloadBytes > 0 && (user.DownloadBytes+user.UploadBytes) >= user.MaxDownloadBytes {
		json.NewEncoder(w).Encode(httpAuthResponse{OK: false})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(httpAuthResponse{OK: true, ID: username})
}

func main() {
	log.SetOutput(io.Discard)

	clientOptions := options.Client().ApplyURI(mongoURI)
	client, err := mongo.Connect(context.TODO(), clientOptions)
	if err != nil {
		log.SetOutput(os.Stderr)
		log.Fatalf("Failed to connect to MongoDB: %v", err)
	}

	err = client.Ping(context.TODO(), nil)
	if err != nil {
		log.SetOutput(os.Stderr)
		log.Fatalf("Failed to ping MongoDB: %v", err)
	}

	userCollection = client.Database(dbName).Collection(collectionName)

	http.HandleFunc("/auth", authHandler)
	log.SetOutput(os.Stderr)
	log.Printf("Auth server starting on %s", listenAddr)
	if err := http.ListenAndServe(listenAddr, nil); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}