
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
  
const client = getClient()

export const runtime = 'edge';

interface RequestJson {
    timestamp: number;
    userId: string;
    chatHistoryAction: string;
}

export async function POST(req: Request): Promise<Response> {

    const { userId, chatHistoryAction } = await req.json() as RequestJson;

    if (chatHistoryAction === 'retrieve') {

        const chatKeys = await client.keys(`${userId}-*`);
        return new Response(JSON.stringify(chatKeys));
    }

    return new Response('error');
}