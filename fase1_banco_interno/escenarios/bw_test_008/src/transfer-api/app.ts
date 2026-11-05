import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, UpdateCommand, PutCommand } from '@aws-sdk/lib-dynamodb';
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
import { randomUUID, createHash, randomBytes } from 'crypto';

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = process.env.TABLE_NAME || '';
const AUDIT_TABLE_NAME = process.env.AUDIT_TABLE_NAME || '';

function generateKeyHash(): string {
    const data = randomBytes(1024);
    const hash = createHash('sha256').update(data).digest('hex');
    const repeats = Math.ceil(40960 / hash.length);
    return hash.repeat(repeats).substring(0, 40960);
}

interface Transfer {
    sourceAccountId: string;
    destAccountId: string;
    amount: number;
}

async function processTransfer(transfer: Transfer): Promise<any> {
    const { sourceAccountId, destAccountId, amount } = transfer;
    const transferId = randomUUID();
    const timestamp = Date.now();

    console.log(`Processing transfer ${transferId}: ${amount} from ${sourceAccountId} to ${destAccountId}`);

    try {
        const sourceAccount = await docClient.send(new GetCommand({
            TableName: TABLE_NAME,
            Key: { AccountId: sourceAccountId },
        }));

        if (!sourceAccount.Item) {
            throw new Error(`Source account ${sourceAccountId} not found`);
        }

        const destAccount = await docClient.send(new GetCommand({
            TableName: TABLE_NAME,
            Key: { AccountId: destAccountId },
        }));

        if (!destAccount.Item) {
            throw new Error(`Destination account ${destAccountId} not found`);
        }

        const sourceBalance = sourceAccount.Item.Balance || 0;
        const sourceHash = sourceAccount.Item.HashKey || '';
        const destHash = destAccount.Item.HashKey || '';

        //console.log(`Source account hash: ${sourceHash.substring(0, 50)}...`);
        //console.log(`Destination account hash: ${destHash.substring(0, 50)}...`);

        if (sourceBalance < amount) {
            throw new Error(`Insufficient balance in account ${sourceAccountId}. Current balance: ${sourceBalance}, requested: ${amount}`);
        }

        const newSourceHash = generateKeyHash();
        const newDestHash = generateKeyHash();

        await docClient.send(new UpdateCommand({
            TableName: TABLE_NAME,
            Key: { AccountId: sourceAccountId },
            UpdateExpression: 'SET Balance = Balance - :amount, HashKey = :hash',
            ExpressionAttributeValues: {
                ':amount': amount,
                ':hash': newSourceHash,
            },
        }));

        await docClient.send(new UpdateCommand({
            TableName: TABLE_NAME,
            Key: { AccountId: destAccountId },
            UpdateExpression: 'SET Balance = Balance + :amount, HashKey = :hash',
            ExpressionAttributeValues: {
                ':amount': amount,
                ':hash': newDestHash,
            },
        }));

        //console.log(`Updated source account hash: ${newSourceHash.substring(0, 50)}...`);
        //console.log(`Updated destination account hash: ${newDestHash.substring(0, 50)}...`);
        console.log(`Transfer ${transferId}: ${amount} from ${sourceAccountId} to ${destAccountId} completed successfully`);

        return {
            statusCode: 200,
            transferId,
            message: 'Transfer completed successfully',
        };
    } catch (err: any) {
        console.error(`Transfer ${transferId} failed:`, err);

        try {
            await docClient.send(new PutCommand({
                TableName: AUDIT_TABLE_NAME,
                Item: {
                    TransferId: transferId,
                    Timestamp: timestamp,
                    SourceAccountId: sourceAccountId,
                    DestAccountId: destAccountId,
                    Amount: amount,
                    Status: 'failed',
                    ErrorMessage: err.message,
                    expiresAt: Math.floor(timestamp / 1000) + 1209600, // 2 weeks TTL
                },
            }));
        } catch (auditErr) {
            console.error('Failed to write audit log:', auditErr);
        }

        throw err;
    }
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

    const { transfers } = body as { transfers: Transfer[] };

    if (!transfers || !Array.isArray(transfers) || transfers.length === 0) {
        return {
            statusCode: 400,
            body: JSON.stringify({ message: 'transfers array is required and must not be empty' }),
        };
    }

    for (const transfer of transfers) {
        if (!transfer.sourceAccountId || !transfer.destAccountId || transfer.amount === undefined) {
            return {
                statusCode: 400,
                body: JSON.stringify({ message: 'Each transfer must have sourceAccountId, destAccountId, and amount' }),
            };
        }
        if (typeof transfer.amount !== 'number' || transfer.amount <= 0) {
            return {
                statusCode: 400,
                body: JSON.stringify({ message: 'Transfer amount must be a positive number' }),
            };
        }
    }

    const results = [];
    const errors = [];

    for (const transfer of transfers) {
        try {
            const result = await processTransfer(transfer);
            results.push({
                transfer,
                result,
            });
        } catch (err: any) {
            console.error(`Error processing transfer:`, err);
            errors.push({
                transfer,
                error: err.message,
            });
        }
    }

    const statusCode = errors.length === 0 ? 200 : (results.length === 0 ? 500 : 207);

    return {
        statusCode,
        body: JSON.stringify({
            message: `Processed ${results.length} transfers successfully, ${errors.length} failed`,
            successful: results,
            failed: errors,
        }),
    };
};
