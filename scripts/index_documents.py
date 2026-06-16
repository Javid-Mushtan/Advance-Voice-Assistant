import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from src.utils.config import OPENROUTER_API_KEY

DOCUMENTS_DIR = "data/documents/"
INDEX_PATH = "data/documents/faiss_index"

def main():
    if not os.path.exists(DOCUMENTS_DIR):
        print("No documents directory found.")
        return

    loader = DirectoryLoader(DOCUMENTS_DIR, glob="**/*.txt", loader_cls=TextLoader)
    # For PDFs you would add PyPDFLoader etc.
    documents = loader.load()
    if not documents:
        print("No .txt documents found.")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
    vectorstore = FAISS.from_documents(docs, embeddings)
    vectorstore.save_local(INDEX_PATH)
    print(f"Index saved with {len(docs)} chunks to {INDEX_PATH}")

if __name__ == "__main__":
    main()