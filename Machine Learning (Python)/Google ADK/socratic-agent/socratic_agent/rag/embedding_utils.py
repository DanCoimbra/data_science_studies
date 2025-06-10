import os
import chromadb
from google import genai


# Import configurations from the core.config module
from socratic_agent.core.config import (
    API_KEY, CHROMA_DB_PATH, DOCUMENTS_PATH, 
    COLLECTION_NAME, EMBEDDING_MODEL, DEFAULT_FILE_ENCODING
)

class GoogleGenAIEmbeddingFunction(chromadb.EmbeddingFunction):
    """Custom embedding function using the Google GenAI SDK."""

    def __init__(self, embedding_model=EMBEDDING_MODEL):
        if not API_KEY:
            raise ValueError("Google API Key is required for GoogleGenAIEmbeddingFunction.")
        self._client = genai.Client(api_key=API_KEY)
        self._embedding_model = embedding_model

    def __call__(self, input_texts: chromadb.Documents) -> chromadb.Embeddings:
        batch_size = 100  # API limit
        embeddings = []
        for i in range(0, len(input_texts), batch_size):
            text_batch = input_texts[i:i + batch_size]
            try:
                response = self._client.models.embed_content(
                    model=self._embedding_model,
                    contents=text_batch
                )
                if not hasattr(response, 'embeddings'):
                    raise ValueError("Response must have an 'embeddings' attribute.")
                if not isinstance(response.embeddings, list):
                    raise ValueError("Response.embeddings must be a list.")
                embeddings.extend([embedding.values for embedding in response.embeddings])
            except Exception as e:
                print(f"Error during embedding batch with Google GenAI: {e}")
                embeddings = None
        return embeddings


def get_embedding_client():
    """Initializes and returns a ChromaDB persistent client."""
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)  # Saves to disk rather than to memory
        if client is None:
            raise RuntimeError("ChromaDB client returned None.")
        return client
    except Exception as e:
        print(f"Error initializing ChromaDB client: {e}")
        return None


def get_or_create_collection(client: chromadb.Client):
    """
    Gets or creates a Chroma collection using COLLECTION_NAME from config.
    Uses GoogleGenAIEmbeddingFunction if api_key is provided (defaults to config.API_KEY),
    otherwise Chroma's default.
    """
    embedding_fn = None
    try:
        embedding_fn = GoogleGenAIEmbeddingFunction(embedding_model=EMBEDDING_MODEL)
    except Exception as e:
        print(f"Failed to initialize GoogleGenAIEmbeddingFunction in ChromaDB: {e}. Falling back to default.")
        embedding_fn = None

    try:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            # Pass None to use Chroma's default (Sentence Transformers)
            embedding_function=embedding_fn
        )
        return collection
    except Exception as e:
        print(f"Error getting or creating ChromaDB collection: {e}")
        return None


def clear_collection(client: chromadb.Client, collection_name: str = COLLECTION_NAME): # Default to config
    """
    Deletes the specified ChromaDB collection if it exists.

    Args:
        client: The ChromaDB client instance.
        collection_name: The name of the collection to delete.
    """

    try:
        client.get_collection(name=collection_name)
        client.delete_collection(name=collection_name)
        print(f"Deleted collection: '{collection_name}'.")
    except Exception as e:
        print(f"An error occurred while trying to delete collection '{collection_name}': {e}")


def embed_documents(client: chromadb.Client, collection: chromadb.Collection):
    """
    Loads documents from DOCUMENTS_PATH, splits them into fixed-size chunks
    of 2000 characters, embeds them, and stores them in ChromaDB.
    """
    if not os.path.exists(DOCUMENTS_PATH):
        print(f"Documents path not found: {DOCUMENTS_PATH}")
        return

    num_files = 0
    chunk_ids = []
    chunk_contents = []
    chunk_metadatas = []
    chunk_size = 2000 # Fixed chunk size

    for filename in os.listdir(DOCUMENTS_PATH):
        if filename.endswith(".txt"):
            filepath = os.path.join(DOCUMENTS_PATH, filename)
            try:
                with open(filepath, "r", encoding=DEFAULT_FILE_ENCODING) as f:
                    content = f.read()
                if not content.strip():
                    print(f"Skipping empty file: {filename}")
                    continue

                # Simple, non-overlapping character-based chunking
                chunk_num_in_file = 0
                for i in range(0, len(content), chunk_size):
                    chunk_text = content[i:i + chunk_size]
                    if not chunk_text.strip():
                        continue
                    chunk_id = f"{'_'.join(filename.split('.')[0].split(' '))}_chunk_{chunk_num_in_file}"
                    chunk_ids.append(chunk_id)
                    chunk_contents.append(chunk_text)
                    chunk_metadatas.append({
                        "source_file": filename,
                        "chunk_num_in_file": chunk_num_in_file,
                        "char_count": len(chunk_text) 
                    })
                    chunk_num_in_file += 1

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    if not chunk_contents:
        print(f"No text chunks found to embed in {DOCUMENTS_PATH} after processing all files.")
        return

    try:
        collection.add(
            ids=chunk_ids, 
            documents=chunk_contents, 
            metadatas=chunk_metadatas
        )
        print(f"\nSuccessfully added/updated {len(chunk_ids)} text chunks from {num_files} files in collection '{collection.name}'.")
    except Exception as e:
        print(f"Error adding text chunks to Chroma collection: {e}")


if __name__ == '__main__':
    print("Testing embedding_utils.py...")
    chroma_client = get_embedding_client()
    assert chroma_client is not None, "Failed to get ChromaDB client."
    clear_collection(chroma_client)
    socratic_collection = get_or_create_collection(chroma_client)
    assert socratic_collection is not None, "Failed to get or create collection."
    assert socratic_collection.name == COLLECTION_NAME, f"Collection name mismatch: {socratic_collection.name}"
    initial_count = socratic_collection.count()
    embed_documents(chroma_client, socratic_collection)
    final_count = socratic_collection.count()
    assert final_count > initial_count, "No documents were added by embed_documents."
    print(f"{final_count - initial_count} chunk(s) added.")
    query_text = "artificial intelligence"
    results = socratic_collection.query(
        query_texts=[query_text], 
        n_results=3,
        include=['documents']
    )
    assert results is not None, "Query returned None results."
    retrieved_docs = results.get('documents')
    assert retrieved_docs is not None, "'documents' key missing."
    assert len(retrieved_docs) == 1, f"Expected 1 list of results, got {len(retrieved_docs)}."
    assert len(retrieved_docs[0]) > 0, f"Query for '{query_text}' returned no documents."
    print(f"Query for '{query_text}' retrieved: {retrieved_docs[0][0][:50]}...")
    print("embedding_utils.py tests passed.") 