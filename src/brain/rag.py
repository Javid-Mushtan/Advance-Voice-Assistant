import os

from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory

from src.utils.config import OPENROUTER_API_KEY

DOCSTORE_PATH = "data/documents/faiss_index"

embeddings = OpenAIEmbeddings(api_key=OPENROUTER_API_KEY,base_url="https://openrouter.ai/api/v1")
if not os.path.exists(os.path.join(DOCSTORE_PATH, "index.faiss")):
    raise FileNotFoundError(f"Document FAISS index not found at {DOCSTORE_PATH}. Run scripts/index_documents.py first.")

doc_vectorstore = FAISS.load_local(DOCSTORE_PATH, embeddings, allow_dangerous_deserialization=True)
doc_retriever = doc_vectorstore.as_retriever(search_kwargs={"k": 4})

contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human","{input}")
    ]
)

llm = ChatOpenAI(api_key=OPENROUTER_API_KEY,base_url="https://openrouter.ai/api/v1",model="openrouter/free")

history_aware_retriever = create_history_aware_retriever(
    llm,doc_retriever,contextualize_q_prompt
)

qa_system_prompt = (
    "You are Javid 0.5 , a helpful AI assistant. "
    "Use the following pieces of retrieved context to answer "
    "the question. If you don't know the answer, say that you "
    "don't know. Keep the answer concise.\n\n{context}"
)
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human","{input}")
    ]
)
question_answer_chain = create_stuff_documents_chain(llm,qa_prompt)

rag_chain = create_retrieval_chain(history_aware_retriever,question_answer_chain)

store = {}
def get_session_history(session_id: str):
    if session_id  not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

conventional_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)