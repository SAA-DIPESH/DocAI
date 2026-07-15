import os
import base64
from functools import lru_cache

from dotenv import load_dotenv
from bson import ObjectId
from pymongo import MongoClient
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# Load Environment Variables
load_dotenv()

class SecretManager:
    """
    Retrieves and decrypts a secret stored in MongoDB.

    All configuration values are loaded from environment variables.
    """

    def __init__(self) -> None:
        self.mongo_uri = os.getenv(
            "MONGO_URI",
            "mongodb://localhost:27017/",
        )
        self.db_name = os.getenv("SECRET_DB")
        self.collection_name = os.getenv("SECRET_COLLECTION")
        self.object_id = os.getenv("OBJECT_ID")
        self.encryption_key = os.getenv("ENCRYPTION_KEY")

        self._validate_environment_variables()

        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    def _validate_environment_variables(self) -> None:
        """
        Validate all required environment variables.
        """

        if not self.db_name:
            raise ValueError("SECRET_DB is missing in the .env file")

        if not self.collection_name:
            raise ValueError(
                "SECRET_COLLECTION is missing in the .env file"
            )

        if not self.object_id:
            raise ValueError("OBJECT_ID is missing in the .env file")

        if not ObjectId.is_valid(self.object_id):
            raise ValueError("OBJECT_ID is not a valid MongoDB ObjectId")

        if not self.encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY is missing in the .env file"
            )

        key_length = len(self.encryption_key.encode("utf-8"))

        if key_length not in (16, 24, 32):
            raise ValueError(
                "ENCRYPTION_KEY must be 16, 24, or 32 bytes long"
            )

    def get_document(self) -> dict:
        """
        Retrieve the configured MongoDB document.
        """

        collection = self.db[self.collection_name]

        document = collection.find_one(
            {
                "_id": ObjectId(self.object_id),
            }
        )

        if not document:
            raise ValueError("Security document not found")

        return document

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt AES-CBC encrypted Base64 text.
        """

        if not encrypted_text:
            raise ValueError("Encrypted text cannot be empty")

        key_bytes = self.encryption_key.encode("utf-8")
        iv = bytes(16)

        try:
            encrypted_bytes = base64.b64decode(
                encrypted_text,
                validate=True,
            )

            cipher = AES.new(
                key_bytes,
                AES.MODE_CBC,
                iv,
            )

            decrypted_bytes = unpad(
                cipher.decrypt(encrypted_bytes),
                AES.block_size,
            )

            return decrypted_bytes.decode("utf-8")

        except Exception as exc:
            raise ValueError(
                "Failed to decrypt the secret"
            ) from exc

    def get_secret(self, field_name: str = "Security") -> str:
        """
        Retrieve and decrypt a secret from the configured document.
        """

        document = self.get_document()

        encrypted_secret = document.get(field_name)

        if not encrypted_secret:
            raise ValueError(
                f"'{field_name}' field was not found in the document"
            )

        return self.decrypt(encrypted_secret)

    def close(self) -> None:
        """
        Close the MongoDB connection.
        """

        self.client.close()



@lru_cache(maxsize=1)
def resolve_openai_api_key() -> str:
    """Retrieve and decrypt the OpenAI API key without import-time side effects."""
    secret_manager = SecretManager()
    try:
        api_key = secret_manager.get_secret(
            os.getenv("SECRET_FIELD", "Security")
        )
    finally:
        secret_manager.close()

    if not api_key:
        raise ValueError("Decrypted OpenAI API key is empty")
    return api_key
