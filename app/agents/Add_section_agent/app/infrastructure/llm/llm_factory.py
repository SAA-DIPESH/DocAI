
import os

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langchain_ollama import ChatOllama


load_dotenv()


class LLMFactory:

    @staticmethod
    def get_llm(
        provider: str = "mistral",
        model: str = None,
        temperature: float = 0.2
    ):

        provider = provider.lower()

        # =========================
        # OPENAI
        # =========================
        if provider == "openai":

            return ChatOpenAI(
                model=model or "gpt-4.1",
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY")
            )

        # =========================
        # MISTRAL API
        # =========================
        elif provider == "mistral":

            return ChatMistralAI(
                model=model or "mistral-large-latest",
                temperature=temperature,
                api_key=os.getenv("MISTRAL_API_KEY")
            )

        # =========================a
        # OLLAMA
        # =========================
        elif provider == "ollama":

            return ChatOllama(
                model=model or "llama3",
                temperature=temperature
            )

        # =========================
        # DEEPSEEK VIA OLLAMA
        # =========================
        elif provider == "deepseek":

            return ChatOllama(
                model=model or "deepseek-r1:latest",
                temperature=temperature
            )

        else:

            raise ValueError(
                f"Unsupported provider: {provider}"
            )