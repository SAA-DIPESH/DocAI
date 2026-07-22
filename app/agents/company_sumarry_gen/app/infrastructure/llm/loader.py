import os

from langchain_openai import ChatOpenAI
from langchain_mistralai import ChatMistralAI
from langchain_ollama import ChatOllama


class LLMFactory:

    @staticmethod
    def get_llm(
        provider: str = None,
        model: str = None,
        temperature: float = 0.2
    ):

        provider = (
            provider
            or os.getenv("LLM_PROVIDER", "mistral")
        ).lower()

        model = (
            model
            or os.getenv("LLM_MODEL")
        )

        if provider == "openai":

            return ChatOpenAI(
                model=model or "gpt-4.1",
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY")
            )

        elif provider == "mistral":

            return ChatMistralAI(
                model=model or "mistral-large-latest",
                temperature=temperature,
                api_key=os.getenv("MISTRAL_API_KEY")
            )

        elif provider == "ollama":

            return ChatOllama(
                model=model or "llama3",
                temperature=temperature
            )

        elif provider == "deepseek":

            return ChatOllama(
                model=model or "deepseek-r1:latest",
                temperature=temperature
            )

        raise ValueError(
            f"Unsupported provider: {provider}"
        )