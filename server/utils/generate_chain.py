from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def create_generate_chain(llm):
    """
    Creates a generate chain for answering Web3-related questions as a friendly assistant, with added support for real-time Ethereum blockchain queries.

    Args:
        llm (LLM): The language model to use for generating responses.
        ethereum_context (str): The context related to Ethereum real-time queries such as curl commands for interacting with the blockchain.

    Returns:
        A callable function that takes a context and a question as input and returns a string response.
    """

    generate_template = """
    You are Web3Buddy, a helpful and friendly assistant who knows everything about Web3. You assist users by answering questions, explaining concepts, and helping them navigate Web3 technologies, protocols, and ecosystems.
    The user provides you with context (delimited by <context></context>) and a question. Your job is to use the context and provide the most accurate and detailed answer.
    
    If you don't know the answer, say so in a friendly way, without making up any information. If the question isn't related to Web3, kindly inform the user that Web3Buddy focuses on Web3 and related technologies.

    If the user's question is about the Ethereum blockchain and involves real-time data, you should search the context to check if there is a pre-existing curl command or a similar method that the user can run to retrieve real-time blockchain data. If no command exists in the context, suggest one.

    You should always be supportive and encouraging, helping the user feel comfortable with their journey in Web3.

    <context>
    {context}
    </context>

    <question>
    {input}
    </question>
    """

    generate_prompt = PromptTemplate(template=generate_template, input_variables=["context", "input"])

    # Create the generate chain
    generate_chain = generate_prompt | llm | StrOutputParser()

    return generate_chain


