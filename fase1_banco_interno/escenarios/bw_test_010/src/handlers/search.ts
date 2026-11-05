import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  ScanCommand,
  GetCommand,
} from "@aws-sdk/lib-dynamodb";
import { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from "aws-lambda";

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

export const handler = async (
  event: APIGatewayProxyEventV2,
): Promise<APIGatewayProxyResultV2> => {
  try {
    const email = event.queryStringParameters?.email;

    if (email) {
      // Get specific user
      const command = new GetCommand({
        TableName: "Users",
        Key: { email },
      });
      const response = await docClient.send(command);

      if (!response.Item) {
        return {
          statusCode: 404,
          body: JSON.stringify({ message: "User not found" }),
        };
      }

      return {
        statusCode: 200,
        body: JSON.stringify(response.Item),
      };
    } else {
      const command = new ScanCommand({
        TableName: "Users",
        Limit: 20,
      });
      const response = await docClient.send(command);

      return {
        statusCode: 200,
        body: JSON.stringify(response.Items || []),
      };
    }
  } catch (error) {
    console.error("Error searching users:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Internal server error" }),
    };
  }
};
