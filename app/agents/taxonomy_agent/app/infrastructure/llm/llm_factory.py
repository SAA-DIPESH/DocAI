from dotenv import load_dotenv
import os
load_dotenv()
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from bson import ObjectId
# from app.services.mongo import _get_database
from ...services.mongo_client import get_document
# def get_int_env(name, default):
#     value = os.getenv(name)
#     return int(value) if value else default


# def _openai_llm():0
#     return ChatOpenAI(
#         model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
#         temperature=0,
#         api_key=os.getenv("OPENAI_API_KEY"),
#         max_tokens=get_int_env("OPENAI_MAX_COMPLETION_TOKENS", 3500),
#     )


# def _mistral_llm():
#     return ChatMistralAI(
#         model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
#         temperature=0,
#         api_key=os.getenv("MISTRAL_API_KEY"),
#     )


# def _ollama_llm():
#     return ChatOllama(
#         model=os.getenv("OLLAMA_MODEL", "deepseek-r1:latest"),
#         base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
#         temperature=0,
#     )


# def _load_llm():
#     provider = os.getenv("LLM_PROVIDER", "openai").lower()

#     if provider == "openai":
#         return _openai_llm()

#     if provider == "mistral":
#         return _mistral_llm()

#     if provider == "ollama":
#         return _ollama_llm()

#     raise ValueError(f"Unsupported provider: {provider}")





def _load_llm(provider: str | None = None):
    provider = (provider or os.getenv("LLM_PROVIDER", "mistral")).lower()

    if provider == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            from ...utils.decrept import decrypt

            security_doc = get_document(
                collection_name="Security",
                filter_query={
                    "_id": ObjectId("6a3944f958430082848fc63d")
                }
            )

            if not security_doc:
                raise Exception("Security document not found")

            encrypted_key = security_doc.get("Security")

            if not encrypted_key:
                raise Exception("Security field not found")

            openai_api_key = decrypt(encrypted_key)
     
        # Fixed: Changed from self.llm to a standard return statement
        return ChatOpenAI(
            model=os.getenv(
                "LLM_MODEL",
                "gpt-4.1"
            ),
            temperature=0,
            api_key=openai_api_key
        )

    elif provider == "mistral":
        return ChatMistralAI(
            model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 0)),
            api_key=os.getenv("MISTRAL_API_KEY"),
        )

    elif provider == "ollama":
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "mistral:7b"),
            temperature=float(os.getenv("LLM_TEMPERATURE", 0)),
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

llm = _load_llm()



# def _openai_llm():
#     from langchain_openai import ChatOpenAI

#     return ChatOpenAI(
#         model=os.getenv("OPENAI_MODEL", "gpt-4"),
#         temperature=0,
#         api_key=os.getenv("OPENAI_API_KEY"),
#     )


# def _mistral_llm():
#     from langchain_mistralai import ChatMistralAI

#     return ChatMistralAI(
#         model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
#         temperature=0,
#         api_key=os.getenv("MISTRAL_API_KEY"),
#     )


# def _ollama_llm():
#     from langchain_ollama import ChatOllama

#     return ChatOllama(
#         model=os.getenv("OLLAMA_MODEL", "deepseek-r1:latest"),
#         temperature=0,
#     )


# def _load_llm():
#     provider = os.getenv("LLM_PROVIDER", "auto").lower()

#     if provider == "openai":
#         return _openai_llm()

#     if provider == "mistral":
#         return _mistral_llm()

#     if provider == "ollama":
#         return _ollama_llm()

#     if os.getenv("OPENAI_API_KEY"):
#         try:
#             return _openai_llm()
#         except ModuleNotFoundError:
#             pass

#     if os.getenv("MISTRAL_API_KEY"):
#         try:
#             return _mistral_llm()
#         except ModuleNotFoundError:
#             pass

#     return _ollama_llm()


# llm = _load_llm()
