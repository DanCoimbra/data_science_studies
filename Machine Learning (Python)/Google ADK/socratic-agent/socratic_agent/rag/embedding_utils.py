import os
import chromadb
from google import genai


# Import configurations from the core.config module
from ..core.config import (
    API_KEY, CHROMA_DB_PATH, DOCUMENTS_PATH, 
    COLLECTION_NAME, EMBEDDING_MODEL, DEFAULT_FILE_ENCODING
)

class GoogleGenAIEmbeddingFunction(chromadb.EmbeddingFunction):
    """Custom embedding function using the Google GenAI SDK."""

    def __init__(self,
                 api_key: str,
                 embedding_model: str = EMBEDDING_MODEL):
        if not api_key:
            # This check is somewhat redundant if API_KEY from config is always used,
            # but good if this class might be instantiated with a direct None key.
            raise ValueError(
                "Google API Key is required for GoogleGenAIEmbeddingFunction.")
        self._client = genai.Client(api_key=api_key)
        self._embedding_model = embedding_model

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
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)  # Saves to disk rather than to memory
    return client


def get_or_create_collection(client: chromadb.Client,
                             api_key: str | None = API_KEY): # Default to API_KEY from config
    """
    Gets or creates a Chroma collection using COLLECTION_NAME from config.
    Uses GoogleGenAIEmbeddingFunction if api_key is provided (defaults to config.API_KEY),
    otherwise Chroma's default.
    """
    embedding_fn = None
    if api_key:
        try:
            embedding_fn = GoogleGenAIEmbeddingFunction(api_key=api_key, embedding_model=EMBEDDING_MODEL)
            print(
                f"Using GoogleGenAIEmbeddingFunction with model: {EMBEDDING_MODEL}")
        except ValueError as ve:
            print(f"ValueError initializing embedding function: {ve}. Falling back to default.")
            embedding_fn = None # Fallback on error
        except Exception as e:
            print(
                f"Failed to initialize GoogleGenAIEmbeddingFunction: {e}. Falling back to default.")
            embedding_fn = None
    else:
        print("No API key available (checked config and argument). Using ChromaDB's default embedding function.")

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        # Pass None to use Chroma's default (Sentence Transformers)
        embedding_function=embedding_fn
    )
    return collection


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
        print(f"Successfully deleted collection: '{collection_name}'.")
    except ValueError:
        print(f"Collection '{collection_name}' not found. No need to delete.")
    except Exception as e:
        print(f"An error occurred while trying to delete collection '{collection_name}': {e}")


def embed_documents(client: chromadb.Client, collection: chromadb.Collection):
    """
    Loads documents from the DOCUMENTS_PATH, splits them into chunks based on a
    3-paragraph or 2000-character rule, embeds these chunks, and stores them in ChromaDB.
    """
    if not os.path.exists(DOCUMENTS_PATH):
        print(f"Documents path not found: {DOCUMENTS_PATH}")
        return

    chunk_ids = []
    chunk_contents = []
    chunk_metadatas = []
    processed_files_count = 0
    min_chars_per_chunk = 2000
    paragraphs_per_grouping = 3

    for filename in os.listdir(DOCUMENTS_PATH):
        if filename.endswith(".txt"):
            filepath = os.path.join(DOCUMENTS_PATH, filename)
            try:
                # Using DEFAULT_FILE_ENCODING from config
                with open(filepath, "r", encoding=DEFAULT_FILE_ENCODING) as f:
                    content = f.read()
                
                if not content.strip():
                    print(f"Skipping empty file: {filename}")
                    continue

                all_paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                
                if not all_paragraphs:
                    print(f"No paragraphs found in file (after stripping): {filename}")
                    continue
                
                current_paragraph_idx = 0
                chunk_num_in_file = 0
                file_chunks_count = 0

                while current_paragraph_idx < len(all_paragraphs):
                    current_chunk_paragraphs_list = []
                    current_chunk_char_count = 0

                    # 1. Gather initial set of paragraphs (up to paragraphs_per_grouping)
                    for _ in range(paragraphs_per_grouping):
                        if current_paragraph_idx < len(all_paragraphs):
                            paragraph = all_paragraphs[current_paragraph_idx]
                            current_chunk_paragraphs_list.append(paragraph)
                            current_chunk_char_count += len(paragraph)
                            current_paragraph_idx += 1
                        else:
                            break # No more paragraphs in the document
                    
                    # 2. If the chunk has content and is still under min_chars_per_chunk, add more paragraphs
                    if current_chunk_paragraphs_list: # Ensure we have at least one paragraph to start
                        while current_chunk_char_count < min_chars_per_chunk and current_paragraph_idx < len(all_paragraphs):
                            paragraph = all_paragraphs[current_paragraph_idx]
                            current_chunk_paragraphs_list.append(paragraph)
                            current_chunk_char_count += len(paragraph)
                            current_paragraph_idx += 1
                        
                        # Finalize the chunk
                        final_chunk_text = "\n\n".join(current_chunk_paragraphs_list)
                        chunk_id = f"{filename}_chunk_{chunk_num_in_file}"
                        
                        chunk_ids.append(chunk_id)
                        chunk_contents.append(final_chunk_text)
                        chunk_metadatas.append({
                            "source_file": filename,
                            "chunk_num_in_file": chunk_num_in_file,
                            "num_paragraphs_in_chunk": len(current_chunk_paragraphs_list),
                            "char_count": len(final_chunk_text) 
                        })
                        chunk_num_in_file += 1
                        file_chunks_count += 1
                    # If current_chunk_paragraphs_list is empty, it means we consumed all paragraphs already.
                    # The outer while loop condition (current_paragraph_idx < len(all_paragraphs)) will handle termination.

                if file_chunks_count > 0:
                    print(f"Successfully created {file_chunks_count} chunks from {filename}.")
                    processed_files_count += 1
                else:
                    print(f"No chunks created from {filename} (e.g., all paragraphs were too short and not enough to meet criteria, or file processed fully by previous logic).")

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
        print(f"\nSuccessfully added/updated {len(chunk_ids)} text chunks from {processed_files_count} files in collection '{collection.name}'.")
        print(f"Current count of items (chunks) in collection: {collection.count()}")
    except Exception as e:
        print(f"Error adding text chunks to Chroma collection: {e}")


if __name__ == '__main__':
    # API_KEY is now imported from config and its existence is checked there.
    # If API_KEY is None, a warning is printed by config.py and get_or_create_collection will use default.
    print(f"Testing embedding_utils.py... API_KEY is set: {bool(API_KEY)}")

    chroma_client = get_embedding_client()
    assert chroma_client is not None, "Failed to get ChromaDB client."
    print("Successfully got ChromaDB client.")

    print(f"Clearing collection '{COLLECTION_NAME}' before test embedding...")
    clear_collection(chroma_client)
    print(f"Collection '{COLLECTION_NAME}' cleared or did not exist.")

    socratic_collection = get_or_create_collection(chroma_client)
    assert socratic_collection is not None, "Failed to get or create collection."
    assert socratic_collection.name == COLLECTION_NAME, f"Collection name mismatch: {socratic_collection.name}"
    print(f"Successfully got/created collection '{socratic_collection.name}'.")
    
    initial_count = socratic_collection.count()
    embed_documents(chroma_client, socratic_collection)
    print(f"embed_documents function executed.")
    
    final_count = socratic_collection.count()
    print(f"Final item count in collection: {final_count}")
    
    assert final_count > initial_count, "No documents were added by embed_documents."
    print(f"{final_count - initial_count} chunk(s) added.")

    print("Attempting a test query on the embedded document...")
    query_text = "artificial intelligence"
    results = socratic_collection.query(
        query_texts=[query_text], 
        n_results=1,
        include=['documents']
    )
    assert results is not None, "Query returned None results."
    retrieved_docs = results.get('documents')
    assert retrieved_docs is not None, "'documents' key missing."
    assert len(retrieved_docs) == 1, f"Expected 1 list of results, got {len(retrieved_docs)}."
    assert len(retrieved_docs[0]) > 0, f"Query for '{query_text}' returned no documents."
    print(f"Query for '{query_text}' retrieved: {retrieved_docs[0][0][:50]}...")
    print("embedding_utils.py tests passed.") 