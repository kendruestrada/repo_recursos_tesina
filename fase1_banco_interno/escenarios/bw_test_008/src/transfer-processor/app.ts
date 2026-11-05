import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand, UpdateCommand, PutCommand } from '@aws-sdk/lib-dynamodb';
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

interface TransferRequest {
    sourceAccountId: string;
    destAccountId: string;
    amount: number;
}

export const handler = async (event: TransferRequest): Promise<any> => {
    const { sourceAccountId, destAccountId, amount } = event;
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

        console.log(`Source account hash: ${sourceHash.substring(0, 50)}...`);
        console.log(`Destination account hash: ${destHash.substring(0, 50)}...`);

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

        console.log(`Updated source account hash: ${newSourceHash.substring(0, 50)}...`);
        console.log(`Updated destination account hash: ${newDestHash.substring(0, 50)}...`);
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
};
