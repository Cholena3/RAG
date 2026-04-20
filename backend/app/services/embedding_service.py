import httpx
import chromadb
from app.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Generates embeddings via Ollama and manages ChromaDB collections."""

    def __init__(self):
        self.chroma = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self.ollama_url = settings.ollama_base_url
        self.model = settings.default_embedding_model

    async def generate_embedding(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.generate_embedding(t) for t in texts]

    def get_or_create_collection(self, collection_name: str):
        return self.chroma.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def delete_collection(self, collection_name: str):
        try:
            self.chroma.delete_collection(collection_name)
        except Exception:
            pass

    async def store_chunks(self, collection_name: str, chunks: list[str],
                           metadatas: list[dict], ids: list[str]):
        collection = self.get_or_create_collection(collection_name)
        embeddings = await self.generate_embeddings_batch(chunks)
        collection.add(documents=chunks, embeddings=embeddings,
                       metadatas=metadatas, ids=ids)
        return len(chunks)

    async def query_similar(self, collection_name: str, query: str,
                            top_k: int = 5) -> dict:
        collection = self.get_or_create_collection(collection_name)
        query_embedding = await self.generate_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return results
