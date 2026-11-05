import json
import uuid
import logging
from db import SimpleConnectionPool

logger = logging.getLogger()
logger.setLevel(logging.INFO)

connection_pool = SimpleConnectionPool(
    minconn=1, 
    maxconn=5, 
    database="production_registry"
)

CID = str(uuid.uuid4())[:8]

def lambda_handler(event, context):
    request_id = getattr(context, 'aws_request_id', 'local-id')
    logger.info(f"START - Node:{CID} - Request:{request_id}")
    
    conn = connection_pool.getconn()
    
    try:
        body_raw = event.get("body") if event else "{}"
        if isinstance(body_raw, str):
            body = json.loads(body_raw)
        else:
            body = body_raw
            
        result = {
            "status": "success",
            "data": {
                "id": body.get("id", "0"),
                "node_ref": CID
            }
        }

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        connection_pool.putconn(conn)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Processing Error"})
        }