import os
import json
import boto3
from aws_synthetics.common import synthetics_logger as logger

def handler(event, context):
    """
    Test_009 Canary Handler
    Tests a REST API endpoint with authorization from SSM Parameter Store
    """
    api_endpoint = os.environ.get('API_ENDPOINT')
    ssm_parameter_name = os.environ.get('SSM_PARAMETER_NAME')

    logger.info(f'Starting API test for endpoint: {api_endpoint}')
    logger.info(f'Fetching authorization token from SSM: {ssm_parameter_name}')

    # Initialize AWS clients
    ssm_client = boto3.client('ssm')

    try:
        # Fetch authorization token from SSM Parameter Store
        logger.info('Retrieving SSM parameter...')
        response = ssm_client.get_parameter(
            Name=ssm_parameter_name,
            WithDecryption=True
        )
        auth_token = response['Parameter']['Value']
        logger.info('Successfully retrieved authorization token from SSM')

        # Make HTTP GET request to the API
        import urllib3
        http = urllib3.PoolManager()

        headers = {
            'X-API-Key': f'{auth_token}',
            'User-Agent': 'AWS-Synthetics-Canary'
        }

        logger.info(f'Making GET request to: {api_endpoint}')
        response = http.request(
            'GET',
            api_endpoint,
            headers=headers,
            timeout=30.0
        )

        # Log response details
        status_code = response.status
        logger.info(f'Response status code: {status_code}')
        logger.info(f'Response headers: {dict(response.headers)}')

        # Verify successful response
        if status_code == 200:
            logger.info('API request successful (200 OK)')

            # This api return binary data so not checking response body

            return {
                'statusCode': 200,
                'body': 'API test passed',
                'metrics': {
                    'httpStatusCode': status_code,
                    'endpoint': api_endpoint
                }
            }
        elif status_code == 401:
            raise Exception(f'Authentication failed: HTTP {status_code}. Check SSM parameter value.')
        elif status_code == 403:
            raise Exception(f'Authorization failed: HTTP {status_code}. Token may not have required permissions.')
        elif status_code == 404:
            raise Exception(f'Endpoint not found: HTTP {status_code}. Check API_ENDPOINT configuration.')
        elif status_code >= 500:
            raise Exception(f'API server error: HTTP {status_code}')
        else:
            raise Exception(f'Unexpected status code: HTTP {status_code}')

    except boto3.exceptions.Boto3Error as e:
        logger.error(f'AWS SSM error: {str(e)}')
        raise Exception(f'Failed to retrieve SSM parameter: {str(e)}')

    except urllib3.exceptions.HTTPError as e:
        logger.error(f'HTTP request error: {str(e)}')
        raise Exception(f'API request failed: {str(e)}')

    except Exception as e:
        logger.error(f'Test failed: {str(e)}')
        raise Exception(f'API test failed: {str(e)}')
