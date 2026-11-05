import os
import json
import urllib3
import threading
from aws_synthetics.common import synthetics_logger as logger

def make_transfer_call(call_number, http, api_endpoint, results, lock):
    try:
        # Each call contains 10 transfers
        transfers = []
        for i in range(10):
            transfers.append({
                'sourceAccountId': 'ACC001',
                'destAccountId': 'ACC002',
                'amount': 10
            })

        transfer_url = f"{api_endpoint}/transfer"
        payload = json.dumps({'transfers': transfers})

        logger.info(f"   Call {call_number}: Sending 10 transfers")
        response = http.request(
            'POST',
            transfer_url,
            body=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60.0
        )

        with lock:
            results.append({
                'call': call_number,
                'status': response.status,
                'response': response.data.decode('utf-8') if response.data else ''
            })

        logger.info(f"   Call {call_number}: Status {response.status}")

    except Exception as e:
        logger.error(f"   Call {call_number}: Error - {str(e)}")
        with lock:
            results.append({
                'call': call_number,
                'status': 'error',
                'error': str(e)
            })

def handler(event, context):
    """
    Test_008 Canary Handler
    Tests concurrent transfers to detect race condition bugs
    """
    api_endpoint = os.environ.get('API_ENDPOINT')

    if not api_endpoint:
        logger.error("API_ENDPOINT environment variable not set")
        raise Exception("Configuration error: missing API_ENDPOINT")

    logger.info(f"Starting Test_008 - Concurrent Transfer Test")
    logger.info(f"API Endpoint: {api_endpoint}")

    http = urllib3.PoolManager()

    try:
        # Step 1: Delete accounts ACC001 and ACC002
        logger.info("Step 1: Deleting existing accounts...")

        for account_id in ['ACC001', 'ACC002']:
            delete_url = f"{api_endpoint}/account?accountId={account_id}"
            logger.info(f"   Deleting account: {account_id}")
            response = http.request('DELETE', delete_url, timeout=30.0)
            logger.info(f"   Delete {account_id}: Status {response.status}")

        # Step 2: Create accounts ACC001 (balance=10000) and ACC002 (balance=0)
        logger.info("Step 2: Creating accounts...")

        accounts = [
            {'accountId': 'ACC001', 'balance': 10000},
            {'accountId': 'ACC002', 'balance': 0}
        ]

        for account in accounts:
            create_url = f"{api_endpoint}/account"
            payload = json.dumps(account)
            response = http.request(
                'POST',
                create_url,
                body=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30.0
            )
            logger.info(f"   Created {account['accountId']}: Status {response.status}, Balance ${account['balance']}")

            if response.status not in [200, 201]:
                logger.error(f"Failed to create account {account['accountId']}")
                raise Exception(f"Account creation failed: {response.status}")

        # Step 3: Make 30 concurrent calls to /transfer endpoint
        logger.info("Step 3: Making 30 concurrent transfer calls...")

        results = []
        lock = threading.Lock()

        # Launch 30 concurrent threads
        threads = []
        for i in range(1, 31):
            thread = threading.Thread(target=make_transfer_call, args=(i, http, api_endpoint, results, lock))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=70)

        logger.info(f"Completed {len(results)}/30 transfer calls")

        # Step 4: Get account details for ACC001 and ACC002
        logger.info("Step 4: Retrieving account balances...")

        accounts_data = {}
        for account_id in ['ACC001', 'ACC002']:
            get_url = f"{api_endpoint}/account?accountId={account_id}"
            response = http.request('GET', get_url, timeout=30.0)

            if response.status != 200:
                logger.error(f"Failed to get account {account_id}: Status {response.status}")
                raise Exception(f"Failed to retrieve account {account_id}")

            account_data = json.loads(response.data.decode('utf-8'))
            accounts_data[account_id] = account_data
            balance = account_data.get('Balance')
            logger.info(f"   {account_id}: Balance = ${balance}")

        # Step 5: Compare balances
        logger.info("Step 5: Verifying balance integrity...")

        balance_acc001 = accounts_data['ACC001'].get('Balance')
        balance_acc002 = accounts_data['ACC002'].get('Balance')
        total_balance = balance_acc001 + balance_acc002

        logger.info(f"   ACC001 Balance: ${balance_acc001}")
        logger.info(f"   ACC002 Balance: ${balance_acc002}")
        logger.info(f"   Total Balance:  ${total_balance}")

        # Test logic: If balances sum to 10000, test FAILS (race condition not detected)
        # If balances don't sum to 10000, test PASSES (race condition detected)
        if total_balance == 10000:
            logger.error("TEST FAILED: Balances sum to 10000 - no race condition detected")
            logger.error("   This means the system is working correctly (no bug)")
            raise Exception(f"Test failed: Total balance is {total_balance}, expected != 10000")
        else:
            logger.info("TEST PASSED: Balances do NOT sum to 10000")
            logger.info(f"   Race condition detected! Balance discrepancy: ${abs(10000 - total_balance)}")
            logger.info("   This confirms the concurrent transfer bug exists")

            return {
                'statusCode': 200,
                'body': 'Test passed - race condition detected',
                'metrics': {
                    'expectedTotal': 10000,
                    'actualTotal': total_balance,
                    'discrepancy': abs(10000 - total_balance),
                    'acc001Balance': balance_acc001,
                    'acc002Balance': balance_acc002
                }
            }

    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise Exception(f"Test_008 failed: {str(e)}")
