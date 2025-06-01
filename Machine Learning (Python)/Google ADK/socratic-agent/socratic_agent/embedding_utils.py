import os
import chromadb
from google import genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Warning: GOOGLE_API_KEY not found. Embedding will fail if a real model is called.")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(CURRENT_DIR, "..", "chroma_db")
DOCUMENTS_PATH = os.path.join(CURRENT_DIR, "..", "documents")
COLLECTION_NAME = "socratic_collection"
# From google-genai PyPI (client.models.embed_content)
EMBEDDING_MODEL = "text-embedding-004"
ENCODING = "latin-1"


class GoogleGenAIEmbeddingFunction(chromadb.EmbeddingFunction):
    """Custom embedding function using the Google GenAI SDK."""

    def __init__(self,
                 api_key: str,
                 embedding_model: str = EMBEDDING_MODEL,
                 task_type: str = "RETRIEVAL_DOCUMENT"):
        if not api_key:
            raise ValueError(
                "Google API Key is required for GoogleGenAIEmbeddingFunction.")
        self._client = genai.Client(api_key=api_key)
        self._embedding_model = embedding_model
        self._task_type = task_type

    def __call__(self,
                 input_texts: chromadb.Documents) -> chromadb.Embeddings:
        all_embeddings = []
        batch_size = 100  # API limit

        for i in range(0, len(input_texts), batch_size):
            batch = input_texts[i:i + batch_size]
            try:
                response = self._client.models.embed_content(
                    model=self._embedding_model,
                    contents=batch
                )
                assert hasattr(
                    response, 'embeddings'), "Response must have an 'embeddings' attribute."
                assert isinstance(
                    response.embeddings, list), "Response.embeddings must be a list."
                all_embeddings.extend([emb.values for emb in response.embeddings])
            except Exception as e:
                print(f"Error during embedding batch with Google GenAI: {e}")
                all_embeddings.extend([[] for _ in batch])

        return all_embeddings


def get_embedding_client():
    """Initializes and returns a ChromaDB persistent client."""
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH)  # Saves to disk rather than to memory
    return client


def get_or_create_collection(client: chromadb.Client,
                             api_key: str | None):
    """
    Gets or creates a Chroma collection.
    Uses GoogleGenAIEmbeddingFunction if api_key is provided, otherwise Chroma's default.
    """
    embedding_fn = None
    if api_key:
        try:
            embedding_fn = GoogleGenAIEmbeddingFunction(api_key=api_key)
            print(
                f"Using GoogleGenAIEmbeddingFunction with model: {EMBEDDING_MODEL}")
        except Exception as e:
            print(
                f"Failed to initialize GoogleGenAIEmbeddingFunction: {e}. Falling back to default.")
            embedding_fn = None
    else:
        print("No API key provided. Using ChromaDB's default embedding function.")

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        # Pass None to use Chroma's default (Sentence Transformers)
        embedding_function=embedding_fn
    )
    return collection


def embed_documents(client: chromadb.Client, collection: chromadb.Collection):
    """
    Loads documents from the DOCUMENTS_PATH, embeds them using Google GenAI,
    and stores them in ChromaDB.
    """
    if not os.path.exists(DOCUMENTS_PATH):
        print(f"Documents path not found: {DOCUMENTS_PATH}")
        return

    doc_ids = []
    doc_contents = []
    for filename in os.listdir(DOCUMENTS_PATH):
        if filename.endswith(".txt"):
            filepath = os.path.join(DOCUMENTS_PATH, filename)
            try:
                with open(filepath, "r", encoding=ENCODING) as f:
                    content = f.read()
                    if content.strip():
                        doc_ids.append(filename)
                        doc_contents.append(content)
                    else:
                        print(f"Skipping empty file: {filename}")
            except Exception as e:
                print(f"Error reading file {filename}: {e}")

    if not doc_contents:
        print(f"No documents found to embed in {DOCUMENTS_PATH}.")
        return

    try:
        collection.add(ids=doc_ids, documents=doc_contents)
        print(
            f"Successfully added/updated {len(doc_ids)} documents in collection '{COLLECTION_NAME}'.")
        print(f"Current count in collection: {collection.count()}")
    except Exception as e:
        print(f"Error adding documents to Chroma collection: {e}")


if __name__ == '__main__':
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("WARNING (main): GOOGLE_API_KEY not found in .env file. ChromaDB will use its default embedding function.")
    chroma_client = get_embedding_client()
    socratic_collection = get_or_create_collection(
        chroma_client, api_key=api_key)
    print(
        f"Successfully connected to ChromaDB and got/created collection '{COLLECTION_NAME}'.")
    initial_count = socratic_collection.count()
    embed_documents(chroma_client, socratic_collection)
    final_count = socratic_collection.count()
    if final_count > initial_count:
        print("\nAttempting a test query...")
        results = socratic_collection.query(
            query_texts=["What is machine learning?"], n_results=1)
        print("Query results:", results['documents'])
    else:
        print("No documents were added to the collection.")
