import { Redis } from "@upstash/redis";

const getClient = () => {
  if (
    !process.env.UPSTASH_REDIS_REST_URL ||
    !process.env.UPSTASH_REDIS_REST_TOKEN
  ) {
    throw new Error(
      "UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set in the environment"
    );
  }
  const client = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  });
  return client;
};

const client = getClient();

export const runtime = 'edge';

interface RequestJson {
  userId: string;
  message: string; // Assuming the message is a string for simplicity
}

export async function POST(req: Request): Promise<Response> {
  try {
    const { userId, message } = await req.json() as RequestJson;

    // Assuming each message is stored with a unique key based on a timestamp
    const messageForRedis = JSON.stringify({
        type: "assistant",
        data: {
          content: message,
        }
      });
  
     await client.lpush(userId, messageForRedis);



    return new Response(JSON.stringify({ success: true }), {
      status: 200, // HTTP status code
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    console.error('Failed to save message:', error);
    return new Response(JSON.stringify({ success: false, error: 'Failed to save message' }), {
      status: 500, // Internal Server Error
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}