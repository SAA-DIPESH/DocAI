from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from app.utils.helpers import SecretManager
from bson import ObjectId
import os



load_dotenv()

# =====================================================
# Get Secrets Key
# ======================================================
secret_manager = SecretManager()

try:
    openai_api_key = secret_manager.get_secret()
finally:
    secret_manager.close()



def create_llm():

    provider = os.getenv("LLM_PROVIDER").lower()

    if provider == "mistral":
        return ChatMistralAI(
            model=os.getenv("MISTRAL_MODEL"),
            api_key=os.getenv("MISTRAL_API_KEY"),
            temperature=0.3,
        )

    elif provider == "openai":
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            api_key=openai_api_key, # if you don't want to use encrypted key than use --> os.getenv("OPENAI_API_KEY")
            temperature=0.3,
        )

    elif provider == "groq":
        return ChatGroq(
            model=os.getenv("GROQ_MODEL"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )

    raise ValueError(f"Unsupported provider: {provider}")
