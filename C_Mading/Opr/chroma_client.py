import chromadb

CHROMA_DB_PATH = "./chroma_db"
CHROMA_COLLECTION_NAME = "medical_knowledge"


def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_medical_collection():
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"description": "medical symptom and department knowledge"}
    )
    return collection