from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

class PineconeRetriever:
    def __init__(self, pinecone_api_key: str, openai_api_key: str, index_name: str, namespace: str):
        if not pinecone_api_key or not openai_api_key:
            raise ValueError("Please provide both Pinecone and OpenAI API keys.")

        # Initialize Pinecone index
        self.index = self._initialize_pinecone(pinecone_api_key, index_name)

        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key, model="text-embedding-ada-002")

        # Create the Pinecone vector store
        self.vector_store = PineconeVectorStore(index=self.index, embedding=self.embeddings, namespace=namespace)

        # Create the retriever
        self.retriever = self.vector_store.as_retriever()

    def _initialize_pinecone(self, api_key: str, index_name: str):
        pc = Pinecone(api_key=api_key)
        return pc.Index(index_name)

    def set_namespace(self, new_namespace: str):
        """
        Updates the namespace for the vector store and retriever.

        Args:
            new_namespace (str): The new namespace to set.
        """
        self.vector_store = PineconeVectorStore(index=self.index, embedding=self.embeddings, namespace=new_namespace)
        self.retriever = self.vector_store.as_retriever()

    def get_retriever(self):
        """
        Returns the current retriever object.

        Returns:
            A retriever object for querying the vector store.
        """
        return self.retriever
