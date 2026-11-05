import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, DeleteCommand } from '@aws-sdk/lib-dynamodb';
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);
const TABLE_NAME = process.env.TABLE_NAME || '';

/**
 * Lambda handler to delete an account
 * DELETE /account?accountId={id}
 */
export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    try {
        const accountId = event.queryStringParameters?.accountId;

        if (!accountId) {
            return {
                statusCode: 400,
                body: JSON.stringify({ message: 'accountId is required' }),
            };
        }

        // Check if account exists
        const getResult = await docClient.send(
            new GetCommand({
                TableName: TABLE_NAME,
                Key: { AccountId: accountId },
            })
        );

        if (!getResult.Item) {
            return {
                statusCode: 404,
                body: JSON.stringify({ message: 'Account not found' }),
            };
        }

        // Delete the account
        await docClient.send(
            new DeleteCommand({
                TableName: TABLE_NAME,
                Key: { AccountId: accountId },
            })
        );

        return {
            statusCode: 200,
            body: JSON.stringify({
                message: 'Account deleted successfully',
                accountId: accountId,
            }),
        };
    } catch (error) {
        console.error('Error deleting account:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ message: 'Internal server error' }),
        };
    }
};
