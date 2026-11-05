const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, GetCommand, UpdateCommand } = require("@aws-sdk/lib-dynamodb");

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

exports.handler = async (event) => {
    const origin = event.headers.origin || event.headers.Origin || "*";
    const authHeader = event.headers.authorization || event.headers.Authorization;
    const sessionAction = event.headers['x-session-action'] || event.headers['X-Session-Action'] || "none";

    console.log(JSON.stringify({
        level: "INFO",
        event: "SecurityAudit",
        requestId: event.requestContext.requestId,
        metadata: {
            origin: origin,
            path: event.path,
            method: event.httpMethod,
            action: sessionAction
        }
    }));

    let userId = "guest";
    if (authHeader && authHeader.startsWith("Bearer ")) {
        try {
            const token = authHeader.split(" ")[1];
            const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64").toString());
            userId = payload.sub; 
        } catch (e) {
            console.error("JWT Error");
        }
    }

    if (sessionAction === 'ACTIVATE' && userId !== "guest") {
        await docClient.send(new UpdateCommand({
            TableName: process.env.TABLE_NAME,
            Key: { userId: userId },
            UpdateExpression: "set session_active = :val",
            ExpressionAttributeValues: { ":val": true }
        }));
    }

    try {
        const result = await docClient.send(new GetCommand({
            TableName: process.env.TABLE_NAME,
            Key: { userId: userId }
        }));

        const responseHeaders = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Session-Action"
        };

        return {
            statusCode: result.Item ? 200 : 404,
            headers: responseHeaders,
            body: JSON.stringify({ 
                data: result.Item || { error: "Not found" },
                session_status: result.Item?.session_active || false 
            })
        };
    } catch (error) {
        return {
            statusCode: 500,
            headers: { "Access-Control-Allow-Origin": origin },
            body: JSON.stringify({ error: "Internal Error" })
        };
    }
};