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

load_dotenv()

pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
fire_api_key = os.getenv("FIRE_API_KEY")

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

def save_documents_to_pinecone(docs: List[Document], vector_store: PineconeVectorStore, source_url: str, namespace: str):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=[
            "\n\n", "\n", " ", ".", ",", "\u200b", "\uff0c", "\u3001", "\uff0e", "\u3002", ""
        ],
        length_function=len,
    )

    for doc in docs:
        chunks = text_splitter.split_text(doc.page_content)

        for chunk in chunks:
            trimmed_metadata = {key: value[:100] if isinstance(value, str) and len(value) > 100 else value
                                for key, value in doc.metadata.items()}
            
            trimmed_metadata['source'] = source_url

            metadata_size = len(json.dumps(trimmed_metadata).encode('utf-8'))
            if metadata_size > 40960:
                print(f"Warning: Metadata size is {metadata_size} bytes, exceeding the limit. Trimming metadata.")
                trimmed_metadata = {key: value[:50] for key, value in trimmed_metadata.items() if isinstance(value, str)}

            chunked_doc = Document(page_content=chunk, metadata=trimmed_metadata)

            uuids = str(uuid4())

            vector_store.add_documents(documents=[chunked_doc], ids=[uuids], namespace=namespace)

def main():
    index_name = "web3-api-index"

    index = initialize_pinecone(pinecone_api_key, index_name, dimension=1536)

    embeddings = OpenAIEmbeddings(api_key=openai_api_key, model="text-embedding-ada-002")

    vector_store = PineconeVectorStore(index=index, embedding=embeddings)

    urls = [
        # "https://docs.rss3.io/guide/core",
        # "https://docs.rss3.io/guide/core/protocols/open-data-protocol",
        # "https://docs.rss3.io/guide/developer",
        # "https://docs.rss3.io/guide/developer/tutorials/get-account-activities-in-batch",
        # "https://docs.rss3.io/guide/developer/tutorials/get-activites-by-network",
        # "https://docs.rss3.io/guide/developer/tutorials/get-activities-by-account",
        # "https://docs.rss3.io/guide/developer/tutorials/get-activities-by-pattern",
        # "https://docs.rss3.io/guide/developer/tutorials/get-activity-by-id",
        # "https://docs.rss3.io/guide/developer/tutorials/get-rss-activity-by-path",
        # "https://docs.rss3.io/guide/developer/api",
        # "https://docs.rss3.io/guide/developer/api/bridge/get-bridging-transaction-by-hash",
        # "https://docs.rss3.io/guide/developer/api/bridge/get-bridging-transactions",
        # "https://docs.rss3.io/guide/developer/api/chips/get-all-chips",
        # "https://docs.rss3.io/guide/developer/api/chips/get-chip-by-id",
        # "https://docs.rss3.io/guide/developer/api/chips/get-chip-image-by-id",
        # "https://docs.rss3.io/guide/developer/api/decentralized/batch-get-accounts-activities",
        # "https://docs.rss3.io/guide/developer/api/decentralized/get-accounts-activities",
        # "https://docs.rss3.io/guide/developer/api/decentralized/get-activity-by-id",
        # "https://docs.rss3.io/guide/developer/api/decentralized/get-network-activities",
        # "https://docs.rss3.io/guide/developer/api/decentralized/get-platform-activities",
        # "https://docs.rss3.io/guide/developer/api/epoch/get-all-epochs",
        # "https://docs.rss3.io/guide/developer/api/epoch/get-epoch-by-id",
        # "https://docs.rss3.io/guide/developer/api/epoch/get-epoch-transaction-by-hash",
        # "https://docs.rss3.io/guide/developer/api/epoch/get-epochs-average-a-p-y",
        # "https://docs.rss3.io/guide/developer/api/epoch/get-node-rewards-by-epoch",
        "https://defillama.com/about",
        "https://wiki.defillama.com/wiki/Main_Page",
        "https://defillama.com/docs/api",

    ]

    namespace1 = "infura-docs"
    namespace2 = "solidity-docs"
    namespace = "defillama-api"

    for url in urls:
        print(f"Crawling URL: {url}")
        loader = FireCrawlLoader(api_key=fire_api_key, url=url, mode="crawl")

        pages = []
        while True:
            try:
                for doc in loader.lazy_load():
                    pages.append(doc)
                    if len(pages) >= 10:
                        save_documents_to_pinecone(pages, vector_store, source_url=url, namespace=namespace)
                        pages = []
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 30))
                    print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                else:
                    raise

        if pages:
            save_documents_to_pinecone(pages, vector_store, source_url=url, namespace=namespace)
            print(f"Documents from {url} saved successfully.")

if __name__ == "__main__":
    main()
