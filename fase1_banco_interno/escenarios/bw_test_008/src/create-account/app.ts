import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, PutCommand, GetCommand } from '@aws-sdk/lib-dynamodb';
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { createHash, randomBytes } from 'crypto';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = process.env.TABLE_NAME || '';

function generateKeyHash(): string {
    const data = randomBytes(1024);
    const hash = createHash('sha256').update(data).digest('hex');
    const repeats = Math.ceil(40960 / hash.length);
    return hash.repeat(repeats).substring(0, 40960);
}

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    if (!event.body) {
        return {
            statusCode: 400,
            body: JSON.stringify({ message: 'Request body is required' }),
        };
    }

    let body;
    try {
        body = JSON.parse(event.body);
    } catch (e) {
        return {
            statusCode: 400,
            body: JSON.stringify({ message: 'Invalid JSON in request body' }),
        };
    }

    const { accountId, balance } = body as { accountId: string; balance: number };

    if (!accountId || balance === undefined) {
        return {
            statusCode: 400,
            body: JSON.stringify({ message: 'accountId and balance are required' }),
        };
    }

    if (typeof balance !== 'number' || balance < 0) {
        return {
            statusCode: 400,
            body: JSON.stringify({ message: 'balance must be a non-negative number' }),
        };
    }

    try {
        const existingAccount = await docClient.send(new GetCommand({
            TableName: TABLE_NAME,
            Key: { AccountId: accountId },
        }));

        if (existingAccount.Item) {
            return {
                statusCode: 409,
                body: JSON.stringify({ message: 'Account already exists' }),
            };
        }

        const accountHash = generateKeyHash();

        await docClient.send(new PutCommand({
            TableName: TABLE_NAME,
            Item: {
                AccountId: accountId,
                Balance: balance,
                HashKey: accountHash,
            },
        }));

        return {
            statusCode: 201,
            body: JSON.stringify({
                message: 'Account created successfully',
                account: { AccountId: accountId, Balance: balance },
            }),
        };
    } catch (err: any) {
        console.error(err);
        return {
            statusCode: 500,
            body: JSON.stringify({
                message: 'Error creating account',
                error: err.message,
            }),
        };
    }
};
