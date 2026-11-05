import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand } from "@aws-sdk/lib-dynamodb";
import { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from "aws-lambda";

const client = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(client);

interface User {
  first_name: string;
  last_name: string;
  birth_date: string;
  genre: string;
  email: string;
}

export const handler = async (
  event: APIGatewayProxyEventV2,
): Promise<APIGatewayProxyResultV2> => {
  try {
    if (!event.body) {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: "Missing request body" }),
      };
    }

    const body = JSON.parse(event.body) as User;
    const { first_name, last_name, birth_date, genre, email } = body;

    // Basic validation
    if (!first_name || !last_name || !birth_date || !genre || !email) {
      return {
        statusCode: 400,
        body: JSON.stringify({ message: "Missing required fields" }),
      };
    }

    const command = new PutCommand({
      TableName: "Users",
      Item: {
        email,
        first_name,
        last_name,
        birth_date,
        genre,
      },
      // ConditionExpression: "attribute_not_exists(email)" // Prevent overwriting existing users if desired, or remove to upsert
    });

    await docClient.send(command);

    return {
      statusCode: 201,
      body: JSON.stringify({ message: "User registered successfully" }),
    };
  } catch (error: any) {
    console.error("Error registering user:", error);

    if (error.name === "ConditionalCheckFailedException") {
      return {
        statusCode: 409,
        body: JSON.stringify({
          message: "User with this email already exists",
        }),
      };
    }

    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Internal server error" }),
    };
  }
};
