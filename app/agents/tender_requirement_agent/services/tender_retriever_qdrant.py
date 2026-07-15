import os
from typing import Any, Dict, Iterator, List, Literal, Optional, TypedDict
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

class TenderRetriever:
    def __init__(self,collection_name: Optional[str] = None,batch_size: int = 50) -> None:
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.collection_name = (collection_name or os.getenv("REQUIREMENT_QDRANT_COLLECTION_NAME"))
        self.batch_size = batch_size

        if not self.qdrant_url:
            raise ValueError(
                "QDRANT_URL is not configured."
            )

        if not self.collection_name:
            raise ValueError(
                "QDRANT_COLLECTION_NAME is not configured."
            )

        if self.batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero."
            )

        self.qdrant_client = QdrantClient(
            url=self.qdrant_url
        )

    def retrieve_chunks(self,tender_id: str) -> Dict[str, Any]:
        tender_id = (
            tender_id.strip()
            if tender_id
            else ""
        )

        if not tender_id:
            raise ValueError("tender_id cannot be empty.")
        
        metadata_filter = Filter(
            must=[
                FieldCondition(
                    key="TenderId",
                    match=MatchValue(
                        value=tender_id
                    ),
                )
            ]
        )

        chunks = self._fetch_all_chunks(metadata_filter)

        return {
            "tender_id": tender_id,
            "total_chunks": len(chunks),
            "chunks": chunks,
        }

    def _fetch_all_chunks(self,metadata_filter: Filter,) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        offset = None

        while True:
            points, next_offset = (
                self.qdrant_client.scroll(
                    collection_name=(
                        self.collection_name
                    ),
                    scroll_filter=metadata_filter,
                    limit=self.batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
            )

            for point in points:
                payload = point.payload or {}

                chunks.append(
                    {
                        "point_id": str(point.id),
                        "tender_id": (
                            payload.get("TenderId")
                        ),
                        "document_id": (
                            payload.get("DocumentId")
                        ),
                        "chunk_id": (
                            payload.get("ChunckId")
                            or payload.get("ChunkId")
                            or str(point.id)
                        ),
                        "document_name": (
                            payload.get("DocumentName")
                        ),
                        "text": payload.get(
                            "Text",
                            "",
                        ),
                        "page_number": (
                            payload.get("PageNumber")
                        ),
                        "related_section": (
                            payload.get(
                                "RelatedSection"
                            )
                        ),
                    }
                )

            if next_offset is None:
                break

            offset = next_offset

        return chunks


# Create Object of Qdrant Retriver Class
tender_retriever = TenderRetriever()