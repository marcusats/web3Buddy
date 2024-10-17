import os
import time
import json
from dotenv import load_dotenv
from uuid import uuid4
from typing import List
import requests

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import FireCrawlLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Load environment variables
load_dotenv()

# Load API keys from the environment
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
fire_api_key = os.getenv("FIRE_API_KEY")  # Use FIRE_API_KEY from .env file

# Initialize Pinecone
def initialize_pinecone(api_key: str, index_name: str, dimension: int = 1536):
    pc = Pinecone(api_key=api_key)
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)
    return pc.Index(index_name)

# Function to save documents to Pinecone
def save_documents_to_pinecone(docs: List[Document], vector_store: PineconeVectorStore, source_url: str, namespace: str):
    # Initialize the text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Define chunk size
        chunk_overlap=200,  # Define overlap between chunks
        separators=[
            "\n\n", "\n", " ", ".", ",", "\u200b", "\uff0c", "\u3001", "\uff0e", "\u3002", ""
        ],  # Custom separators for languages without word boundaries
        length_function=len,
    )

    for doc in docs:
        # Split the document content into smaller chunks
        chunks = text_splitter.split_text(doc.page_content)

        # For each chunk, create a new document and add source_url to metadata
        for chunk in chunks:
            trimmed_metadata = {key: value[:100] if isinstance(value, str) and len(value) > 100 else value
                                for key, value in doc.metadata.items()}
            
            # Add source_url as metadata
            trimmed_metadata['source'] = source_url

            # Check the size of metadata to ensure it's below the Pinecone limit
            metadata_size = len(json.dumps(trimmed_metadata).encode('utf-8'))
            if metadata_size > 40960:
                print(f"Warning: Metadata size is {metadata_size} bytes, exceeding the limit. Trimming metadata.")
                trimmed_metadata = {key: value[:50] for key, value in trimmed_metadata.items() if isinstance(value, str)}

            # Create a new Document object for each chunk
            chunked_doc = Document(page_content=chunk, metadata=trimmed_metadata)

            # Generate UUID for the chunked document
            uuids = str(uuid4())

            # Add the chunked document to Pinecone with the specified namespace
            vector_store.add_documents(documents=[chunked_doc], ids=[uuids], namespace=namespace)

# Main function to crawl and store documents
def main():
    # Set Pinecone index name
    index_name = "web3-api-index"

    # Initialize Pinecone index with correct dimension
    index = initialize_pinecone(pinecone_api_key, index_name, dimension=1536)

    # Initialize OpenAI embeddings (use text-embedding-ada-002 for 1536 dimension)
    embeddings = OpenAIEmbeddings(api_key=openai_api_key, model="text-embedding-ada-002")

    # Initialize Pinecone vector store
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)

    # List of URLs to crawl
    urls = [
        "https://docs.soliditylang.org/en/develop/index.html",
        "https://docs.soliditylang.org/en/develop/introduction-to-smart-contracts.html",
        "https://docs.soliditylang.org/en/develop/solidity-by-example.html",
        "https://docs.soliditylang.org/en/develop/installing-solidity.html",
        "https://docs.soliditylang.org/en/develop/layout-of-source-files.html",
        "https://docs.soliditylang.org/en/develop/structure-of-a-contract.html",
        "https://docs.soliditylang.org/en/develop/structure-of-a-contract.html",
        "https://docs.soliditylang.org/en/develop/units-and-global-variables.html",
        "https://docs.soliditylang.org/en/develop/control-structures.html",
        "https://docs.soliditylang.org/en/develop/contracts.html",
        "https://docs.soliditylang.org/en/develop/assembly.html",
        "https://docs.soliditylang.org/en/develop/cheatsheet.html",
        "https://docs.soliditylang.org/en/develop/grammar.html",
        "https://docs.soliditylang.org/en/develop/using-the-compiler.html",
        "https://docs.soliditylang.org/en/develop/analysing-compilation-output.html",
        "https://docs.soliditylang.org/en/develop/ir-breaking-changes.html",
        "https://docs.soliditylang.org/en/develop/internals/layout_in_storage.html",
        "https://docs.soliditylang.org/en/develop/internals/layout_in_memory.html",
        "https://docs.soliditylang.org/en/develop/internals/layout_in_calldata.html",
        "https://docs.soliditylang.org/en/develop/internals/variable_cleanup.html",
        "https://docs.soliditylang.org/en/develop/internals/source_mappings.html",
        "https://docs.soliditylang.org/en/develop/internals/optimizer.html",
        "https://docs.soliditylang.org/en/develop/metadata.html",
        "https://docs.soliditylang.org/en/develop/abi-spec.html",
        "https://docs.soliditylang.org/en/develop/security-considerations.html",
        "https://docs.soliditylang.org/en/develop/bugs.html",
        "https://docs.soliditylang.org/en/develop/050-breaking-changes.html",
        "https://docs.soliditylang.org/en/develop/060-breaking-changes.html",
        "https://docs.soliditylang.org/en/develop/070-breaking-changes.html",
        "https://docs.soliditylang.org/en/develop/080-breaking-changes.html",
        "https://docs.soliditylang.org/en/develop/natspec-format.html",
        "https://docs.soliditylang.org/en/develop/smtchecker.html",
        "https://docs.soliditylang.org/en/develop/yul.html",
        "https://docs.soliditylang.org/en/develop/path-resolution.html",
        "https://docs.soliditylang.org/en/develop/style-guide.html",
        "https://docs.soliditylang.org/en/develop/common-patterns.html",
        "https://docs.soliditylang.org/en/develop/resources.html",
        "https://docs.soliditylang.org/en/develop/language-influences.html",
    ]

    # Set the namespace
    namespace1 = "infura-docs"
    namespace = "solidity-docs"


    # Iterate over URLs and crawl them using FireCrawlLoader with lazy loading
    for url in urls:
        print(f"Crawling URL: {url}")
        loader = FireCrawlLoader(api_key=fire_api_key, url=url, mode="crawl")

        pages = []
        while True:
            try:
                for doc in loader.lazy_load():
                    pages.append(doc)
                    if len(pages) >= 10:  # Process in batches of 10
                        save_documents_to_pinecone(pages, vector_store, source_url=url, namespace=namespace)  # Pass the URL as source and use namespace
                        pages = []  # Reset the batch
                break  # Exit the loop if successful
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 30))
                    print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                else:
                    raise  # Re-raise the exception if it's not a rate limit error

        # Save remaining documents, if any
        if pages:
            save_documents_to_pinecone(pages, vector_store, source_url=url, namespace=namespace)  # Pass the URL as source and use namespace
            print(f"Documents from {url} saved successfully.")

if __name__ == "__main__":
    main()
