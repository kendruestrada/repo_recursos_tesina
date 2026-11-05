import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = process.env.TABLE_NAME || '';

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    const accountId = event.queryStringParameters?.accountId;

    if (!accountId) {
        return {
            statusCode: 400,
            body: JSON.stringify({ message: 'accountId query parameter is required' }),
        };
    }

    try {
        const result = await docClient.send(new GetCommand({
            TableName: TABLE_NAME,
            Key: { AccountId: accountId },
        }));

        if (!result.Item) {
            return {
                statusCode: 404,
                body: JSON.stringify({ message: 'Account not found' }),
            };
        }

        return {
            statusCode: 200,
            body: JSON.stringify(result.Item),
        };
    } catch (err: any) {
        console.error(err);
        return {
            statusCode: 500,
            body: JSON.stringify({
                message: 'Error retrieving account',
                error: err.message,
            }),
        };
    }
};
