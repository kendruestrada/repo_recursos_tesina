#!/bin/bash

echo "Starting two concurrent calls..."

# Run command1 in the background
curl --location 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/transfer' \
--header 'Content-Type: application/json' \
--data '{
    "transfers": [
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      },
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      },
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      }
    ]
  }' &
PID1=$! # Optional: capture the process ID

# Run command2 in the background
curl --location 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/transfer' \
--header 'Content-Type: application/json' \
--data '{
    "transfers": [
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      },
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      },
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      }
    ]
  }' &
PID2=$! # Optional: capture the process ID

# Run command3 in the background
curl --location 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/transfer' \
--header 'Content-Type: application/json' \
--data '{
    "transfers": [
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      },
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      },
      {
        "sourceAccountId": "ACC001",
        "destAccountId": "ACC002",
        "amount": 1
      }
    ]
  }' &
PID3=$! # Optional: capture the process ID

echo "Calls are running concurrently. Waiting for them to finish..."

# Wait for all background jobs to complete
wait

echo "Calls have finished."
