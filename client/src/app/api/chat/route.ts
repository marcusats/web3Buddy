import { NextRequest, NextResponse } from "next/server";
import { Redis } from "@upstash/redis";
import { UpstashRedisChatMessageHistory } from "@langchain/community/stores/message/upstash_redis";
import { ChatOpenAI,  OpenAIEmbeddings} from "@langchain/openai";
import { BufferMemory } from "langchain/memory";
import { ConversationChain } from "langchain/chains";
import { StreamingTextResponse, Message as VercelChatMessage, LangChainStream, OpenAIStream } from 'ai';
import { Calculator } from "langchain/tools/calculator";
import { Pinecone } from '@pinecone-database/pinecone';
import {
    ChatPromptTemplate,
    MessagesPlaceholder,
} from "@langchain/core/prompts";
import { AgentExecutor, createOpenAIFunctionsAgent } from "langchain/agents";
import { AIMessage, ChatMessage, HumanMessage } from "@langchain/core/messages";
import { PineconeStore } from "@langchain/pinecone";
import { createRetrieverTool } from "langchain/tools/retriever";
import { TavilySearchResults } from "@langchain/community/tools/tavily_search";
import axios from 'axios';
import { DynamicStructuredTool } from "@langchain/core/tools";
import { z } from "zod";

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

const getPineconeClient = () => {
    if (
      !process.env.PINECONE_API_KEY 
    ) {
      throw new Error(
        "PINECONE_API_KEY and PINECONE_API_ENDPOINT must be set in the environment"
      );
    }
    const client = new Pinecone({
      apiKey: process.env.PINECONE_API_KEY,
    });
    return client;
};

const AGENT_SYSTEM_TEMPLATE = `You are very powerful technical assistant, with vast knowledge about the TheGraph Protocol and its ecosystem. You can answer questions, perform calculations, and search for information. You can also use the Tavily search tool to find information on the web`
const INDEX_NAME = "thegraph";

const client = getClient();
const pinecone = getPineconeClient();

export const runtime = 'edge';

const convertVercelMessageToLangChainMessage = (message: VercelChatMessage) => {
    if (message.role === "user") {
      return new HumanMessage(message.content);
    } else if (message.role === "assistant") {
      return new AIMessage(message.content);
    } else {
      return new ChatMessage(message.content, message.role);
    }
};
  

export async function POST(req: Request) {

 try{ 

    const { messages, userId, loadMessages } = await req.json();
 
  
  
    if (userId && loadMessages) {
        const populateHistoricChat = await client.lrange(userId, 0, -1);
        return new Response(JSON.stringify(populateHistoricChat));
    }
    const embeddings = new OpenAIEmbeddings({openAIApiKey: process.env.OPENAI_API_KEY})
    const pineconeIndex = await pinecone.Index(INDEX_NAME);
    const vectorStore = await PineconeStore.fromExistingIndex(
        embeddings ,
        { pineconeIndex }
    );
    const retriever = vectorStore.asRetriever();

    const retrieverTool = await createRetrieverTool(retriever, {
        name: "thegraph_search",
        description:
        "Search for information about TheGraph Protocol. For any questions about TheGraph, you must use this tool! It is very powerful and can find information about TheGraph Protocol and its ecosystem. You can ask questions like 'What is TheGraph Protocol?' or 'What is the latest news about",
    });
    const searchTool = new TavilySearchResults({apiKey: process.env.TAVILY_API_KEY});

    const subgraphCreationTool = new DynamicStructuredTool({
        name: "subgraph_creation",
        description: "If there's an user that asks to create a subgraph, go for this. This tools must be used when trying to create the subgraph for TheGraph Protocol. Make sure that you have the correct information before using this tool. Which it is the contract address, the network, the start block, the protocol the name of the slug and the name for the repo. You should ask for all of the information. return for the codesandbox link",
        schema: z.object({
            contract: z.string().describe("The contract address for the subgraph"),
            network: z.string().describe("The network for the subgraph"),
            startBlock: z.string().describe("The start block for the subgraph"),
            protocol: z.string().describe("The protocol for the subgraph"),
            slug: z.string().describe("The name of the slug for the subgraph"),
            repoName: z.string().describe("The name of the repo for the subgraph"),
            link: z.string().describe("The link for the codesandbox"),
        }),
        func: async (
            { contract, network, startBlock, protocol, slug, repoName }:
            { contract: string, network:string, startBlock: string, protocol: string, slug: string, repoName:string} ) => {
                try {
                    console.log('contract', contract);
                    const response = await fetch('http://localhost:3001/create-subgraph', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            contract,
                            network,
                            startBlock,
                            protocol,
                            slug,
                            repoName,
                        }),
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const data = await response.text();
                    
                    return data;
                                
                } catch (error: any) {
                    console.error(`Error: ${error}`);
                    throw new Error(`Error making request: ${error}`);
                }
            },
        });

    const tools = [new Calculator(), searchTool, subgraphCreationTool, retrieverTool];
    
    const model = new ChatOpenAI({
        modelName: "gpt-4",
        temperature: 0,
        streaming: true,
        openAIApiKey: process.env.OPENAI_API_KEY,
    });

    const prompt = ChatPromptTemplate.fromMessages([
        ["system", AGENT_SYSTEM_TEMPLATE],
        new MessagesPlaceholder("chat_history"),
        ["human", "{input}"],
        new MessagesPlaceholder("agent_scratchpad"),
    ]);

    const agent = await createOpenAIFunctionsAgent({
        llm: model,
        tools,
        prompt,
    });

    const agentExecutor = new AgentExecutor({
        agent,
        tools,

    });

    const _messages = (messages ?? []).filter(
        (message: VercelChatMessage) =>
          message.role === "user" || message.role === "assistant",
    );
    const previousMessages = _messages
      .slice(0, -1)
      .map(convertVercelMessageToLangChainMessage);

      
    
      const lastMessage = _messages[_messages.length - 1].content;
        const lastMessageRole = _messages[_messages.length - 1].role;
      
      const messageForRedis = JSON.stringify({
        type: lastMessageRole,
        data: {
          content: lastMessage,
        }
      });
  
     await client.lpush(userId, messageForRedis);
 
    


    const logStream = await agentExecutor.streamLog({
        input: lastMessage,
        chat_history: previousMessages,
    });
    const textEncoder = new TextEncoder();
      const transformStream = new ReadableStream({
        async start(controller) {
          for await (const chunk of logStream) {
            if (chunk.ops?.length > 0 && chunk.ops[0].op === "add") {
              const addOp = chunk.ops[0];
              if (
                addOp.path.startsWith("/logs/ChatOpenAI") &&
                typeof addOp.value === "string" &&
                addOp.value.length
              ) {
                controller.enqueue(textEncoder.encode(addOp.value));
              }
            }
          }
          controller.close();
        },
      });

      
    return new StreamingTextResponse(transformStream);

   
 } catch (e) {
     console.error(e);
     return new Response('error');
 }
};
