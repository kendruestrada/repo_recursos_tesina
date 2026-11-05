import json
import boto3
import os
import time
import requests

cognito = boto3.client("cognito-idp")
user_pool_id = os.environ.get("USER_POOL_ID")
group_name = os.environ.get("GROUP_NAME", "premium_users")


def lambda_handler(event, context):

    print(f"[INFO] Received DynamoDB Stream event with {len(event['Records'])} records")

    for record in event["Records"]:
        if record["eventName"] == "INSERT":
            try:
                # Extract user_id from DynamoDB Stream
                new_image = record["dynamodb"]["NewImage"]
                user_id = new_image["user_id"]["S"]
                subscription_status = new_image.get("subscription_status", {}).get(
                    "S", ""
                )

                print(f"[INFO] Processing permissions for user_id: {user_id}")
                print(f"[INFO] Subscription status: {subscription_status}")

                if subscription_status == "active":
                    print(
                        f"[INFO] Starting Cognito group assignment for user: {user_id}"
                    )

                    processor_url = os.environ.get("PROCESSOR_ENDPOINT_URL")
                    processor_response = requests.get(processor_url)
                    print(
                        f"[INFO] Processor endpoint response: {processor_response.text}"
                    )

                    print(f"[INFO] Adding user {user_id} to group {group_name}")
                    cognito.admin_add_user_to_group(
                        UserPoolId=user_pool_id, Username=user_id, GroupName=group_name
                    )

                    print(f"[SUCCESS] User {user_id} added to {group_name} group")

            except Exception as e:
                print(f"[ERROR] Failed to sync permissions: {str(e)}")
                raise  # Re-raise para que vaya a DLQ

    return {"statusCode": 200, "body": json.dumps("Permissions synced")}
