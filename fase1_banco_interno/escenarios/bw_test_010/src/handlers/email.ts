import { DynamoDBStreamEvent } from "aws-lambda";
import { SESClient, SendEmailCommand } from "@aws-sdk/client-ses";

const sesClient = new SESClient({});

const SOURCE_EMAIL = process.env.SOURCE_EMAIL;
const EMAIL_CHARSET = process.env.EMAIL_CHARSET;

if (!SOURCE_EMAIL || !EMAIL_CHARSET) {
  throw new Error("Missing SOURCE_EMAIL or EMAIL_CHARSET environment variables");
}

export const handler = async (event: DynamoDBStreamEvent): Promise<void> => {
  for (const record of event.Records) {
    if (
      (record.eventName === "INSERT" || record.eventName === "MODIFY") &&
      record.dynamodb?.NewImage
    ) {
      const newImage = record.dynamodb.NewImage;

      const email = newImage.email.S;
      const firstName = newImage.first_name.S;
      const lastName = newImage.last_name.S;
      const birthDate = newImage.birth_date.S;

      if (!email || !firstName) {
        console.warn("Skipping record with missing email or first_name");
        continue;
      }

      const templateContent = `
        Hello ${firstName} ${lastName},
        
        Welcome! We have registered your details:
        Birth Date: ${birthDate}
        
        Best regards,
        The Team
      `;

      try {
        const command = new SendEmailCommand({
          Source: SOURCE_EMAIL,
          Destination: {
            ToAddresses: [email],
          },
          Message: {
            Subject: {
              Data: "Welcome to our Service",
              Charset: EMAIL_CHARSET,
            },
            Body: {
              Text: {
                Data: templateContent,
                Charset: EMAIL_CHARSET,
              },
            },
          },
        });

        console.log(JSON.stringify({
          event: "DispatchingEmailToSES",
          recipient: email,
          ses_payload: command.input
        }));

        await sesClient.send(command);
        console.log(`Email sent to ${email}`);
      } catch (error) {
        console.error(`Error sending email to ${email}:`, error);
      }
    }
  }
};
