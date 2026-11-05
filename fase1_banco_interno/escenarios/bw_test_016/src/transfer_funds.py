import json
import os
import uuid
import urllib.request
from resource_registry import reserve_resource, release_resource

PROCESSOR_URL = os.environ.get('INTERNAL_PROC_ENDPOINT')

def verify_settlement_window(acc_id):
    try:
        with urllib.request.urlopen(PROCESSOR_URL, timeout=20) as response:
            return response.getcode() == 200
    except:
        return False

def handler(event, context):
    data = json.loads(event.get('body', '{}'))
    source = data.get('from_account')
    target = data.get('to_account')
    tx_id = str(uuid.uuid4())

    if not source or not target:
        return {"statusCode": 400, "body": "Invalid Params"}

    print(f"TXN: {tx_id} | SRC: {source} | DST: {target} | STATE: START")

    try:
        reserve_resource(f"res:{source}", tx_id)
        print(f"TXN: {tx_id} | RES: {source} | PH: 1 | STATE: RESERVED")

        verify_settlement_window(source)

        print(f"TXN: {tx_id} | RES: {target} | PH: 2 | STATE: ATTEMPT")
        reserve_resource(f"res:{target}", tx_id)

        release_resource(f"res:{source}", tx_id)
        release_resource(f"res:{target}", tx_id)

        print(f"TXN: {tx_id} | STATE: FINISH")

        return {
            "statusCode": 200,
            "body": json.dumps({"status": "ok", "trace": tx_id})
        }

    except Exception as e:
        print(f"TXN: {tx_id} | ERROR: {type(e).__name__} | MSG: {str(e)}")
        release_resource(f"res:{source}", tx_id)
        release_resource(f"res:{target}", tx_id)
        return {"statusCode": 500, "body": "Service Unavailable"}