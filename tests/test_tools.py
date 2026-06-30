from datetime import datetime

from langchain_groq import ChatGroq

from src.utils.config import GROQ_API_KEY


def main():
    today = datetime.now().strftime()
    print(today)


if __name__ == "__main__":
    main()