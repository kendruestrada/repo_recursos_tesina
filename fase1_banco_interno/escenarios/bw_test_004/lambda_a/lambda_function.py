import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("TABLE_NAME", "subscriptions")
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    """
    Lambda A - Create Subscription
    """

    print(f"[INFO] Received event: {json.dumps(event)}")

    try:
        # Parse body
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("user_id")
        plan_type = body.get("plan_type", "premium")

        if not user_id:
            print("[ERROR] Missing user_id in request")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "user_id is required"}),
            }

        print(f"[INFO] Processing subscription for user: {user_id}")

        # Create subscription in DynamoDB
        item = {
            "user_id": user_id,
            "subscription_status": "active",
            "plan_type": plan_type,
            "created_at": datetime.utcnow().isoformat(),
        }

        table.put_item(Item=item)

        print(f"[INFO] Subscription created successfully for user_id: {user_id}")
        print(f"[INFO] Subscription status: active, plan: {plan_type}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Subscription created successfully",
                    "user_id": user_id,
                    "status": "active",
                }
            ),
        }

    except Exception as e:
        print(f"[ERROR] Failed to create subscription: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
