#!/bin/bash

PROFILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --profile <aws-profile>"
            exit 1
            ;;
    esac
done

if [ -z "$PROFILE" ]; then
    echo "Error: --profile parameter is required"
    echo "Usage: $0 --profile <aws-profile>"
    exit 1
fi

JSON_FILE="claude-code/projects.json"

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: $JSON_FILE not found"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed"
    exit 1
fi

echo "Checking CloudWatch Log Groups"
echo "Profile: $PROFILE"
echo "================================"
echo ""

projects=$(jq -r '.projects[] | @json' "$JSON_FILE")

while IFS= read -r project; do
    project_name=$(echo "$project" | jq -r '.name')
    logs=$(echo "$project" | jq -r '.logs[]')

    echo "Project: $project_name"
    echo "---"

    while IFS= read -r log_group; do
        printf "  %-50s" "$log_group"

        if aws logs describe-log-groups --log-group-name-prefix "$log_group" --profile "$PROFILE" --output json 2>/dev/null | jq -e ".logGroups[] | select(.logGroupName == \"$log_group\")" > /dev/null 2>&1; then
            last_event=$(aws logs describe-log-streams --log-group-name "$log_group" --profile "$PROFILE" --order-by LastEventTime --descending --max-items 1 --output json 2>/dev/null | jq -r '.logStreams[0].lastEventTimestamp // empty')

            if [ -n "$last_event" ]; then
                last_date=$(date -r $((last_event / 1000)) '+%Y-%m-%d %H:%M:%S' 2>/dev/null)
                days_ago=$(( ($(date +%s) - (last_event / 1000)) / 86400 ))
                echo "EXISTS | HAS DATA | Last: $last_date ($days_ago days ago)"
            else
                echo "EXISTS | NO DATA"
            fi
        else
            echo "NOT FOUND"
        fi
    done <<< "$logs"

    echo ""
done <<< "$projects"

echo "================================"
echo "Check completed"
