# from qdrant_client import QdrantClient
# from qdrant_client.models import (
#     VectorParams,
#     Distance,
#     PointStruct
# )

# # from infrastructure.llm.embedding_model import (
# #     get_query_embedding,
# #     get_document_embeddings
# # )

# import uuid


# class QdrantService:

#     COLLECTION_NAME = "CPDoccuments"

#     client = QdrantClient(
#         url="http://localhost:6333"
#     )

#     @staticmethod
#     def create_collection(vector_size: int = 1536):

#         collections = QdrantService.client.get_collections().collections

#         existing = [
#             collection.name
#             for collection in collections
#         ]

#         if QdrantService.COLLECTION_NAME in existing:
#             print("Collection already exists")
#             return

#         QdrantService.client.create_collection(
#             collection_name=QdrantService.COLLECTION_NAME,
#             vectors_config=VectorParams(
#                 size=vector_size,
#                 distance=Distance.COSINE
#             )
#         )

#         print("Collection created successfully")

#     @staticmethod
#     def insert_documents(documents: list[str]):

#         embeddings = get_document_embeddings(documents)

#         points = []

#         for document, vector in zip(documents, embeddings):

#             points.append(
#                 PointStruct(
#                     id=str(uuid.uuid4()),
#                     vector=vector,
#                     payload={
#                         "text": document
#                     }
#                 )
#             )

#         QdrantService.client.upsert(
#             collection_name=QdrantService.COLLECTION_NAME,
#             points=points
#         )

#         print("Documents inserted successfully")

#     @staticmethod
#     def search(query: str, limit: int = 5):

#         query_vector = get_query_embedding(query)

#         results = QdrantService.client.search(
#             collection_name=QdrantService.COLLECTION_NAME,
#             query_vector=query_vector,
#             limit=limit
#         )

#         return results

#     @staticmethod
#     def get_all_collections():

#         return QdrantService.client.get_collections()

#     @staticmethod
#     def delete_collection():

#         QdrantService.client.delete_collection(
#             collection_name=QdrantService.COLLECTION_NAME
#         )

#         print("Collection deleted")

# QdrantService.create_collection()
# # QdrantService.insert_documents([
# #     "Apple is an AcompanyI ",
# #     "Google works on Gemini"
# # ])
