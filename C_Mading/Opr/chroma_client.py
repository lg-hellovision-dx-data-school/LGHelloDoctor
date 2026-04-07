# Opr/chroma_client.py

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_DB_PATH = "./chroma_db"
CHROMA_COLLECTION_NAME = "medical_knowledge"


def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_medical_collection():
    client = get_chroma_client()

    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name="jhgan/ko-sroberta-multitask",
        device="cpu",
        normalize_embeddings=False,
    )

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "medical symptom and department knowledge"},
    )
    return collection