import os

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from src.utils.config import OPENROUTER_API_KEY
from src.utils.logger import logger

MEMORY_PATH = "data/memory/"

class LongTermMemory:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(api_key=OPENROUTER_API_KEY,base_url="https://openrouter.ai/api/v1")
        index_file = os.path.join(MEMORY_PATH, "index.faiss")
        if os.path.exists(index_file):
            self.store = FAISS.load_local(MEMORY_PATH, self.embeddings, allow_dangerous_deserialization=True)
        else:
            self.store = None

    def remember(self, fact: str):
        fact = fact.strip()
        if self.store is not None:
            existing = self.store.similarity_search(fact, k=1)
            if existing and existing[0].page_content.strip() == fact:
                logger.info(f"Fact already stored, skipping duplicate: {fact}")
                return
        doc = Document(page_content=fact, metadata={"source": "user"})
        if self.store is None:
            self.store = FAISS.from_documents([doc], self.embeddings)
        else:
            self.store.add_documents([doc])
        self.store.save_local(MEMORY_PATH)
        logger.info(f"Fact remembered: {fact}")

    def recall(self, query: str, k: int = 3) -> str:
        if self.store is None:
            return "No memories found."
        docs = self.store.similarity_search(query, k=k)
        if not docs:
            return "No relevant memory."
        return "\n".join([d.page_content for d in docs])