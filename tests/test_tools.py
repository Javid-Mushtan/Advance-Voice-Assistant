from langchain_groq import ChatGroq

from src.utils.config import GROQ_API_KEY


def main():
    model = "mixtral-8x7b-32768"
    llm = ChatGroq(
        model=model,
        api_key=GROQ_API_KEY
    )

    response = llm.invoke("Explain SGD in simple terms")
    print(response.content)


if __name__ == "__main__":
    main()