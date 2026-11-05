#!/bin/bash

echo "Starting two concurrent calls..."

# Run command1 in the background
curl --location 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/report' \
--header 'X-API-Key: xrLDfK30tR1NUXtylScU5llNmAyXZKf4sAeSOhk9' -s -I -X GET &
PID1=$! # Optional: capture the process ID

# Run command2 in the background
curl --location 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/v1/report' \
--header 'X-API-Key: xrLDfK30tR1NUXtylScU5llNmAyXZKf4sAeSOhk9' -s -I -X GET &
PID2=$! # Optional: capture the process ID

echo "Calls are running concurrently. Waiting for them to finish..."

# Wait for all background jobs to complete
wait

echo "Both calls have finished."
