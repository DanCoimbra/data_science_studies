import chromadb

# Import configurations from the core.config module
from socratic_agent.core.config import API_KEY # Only API_KEY is directly needed here for now
# Other configs like COLLECTION_NAME are used by functions imported from embedding_utils

# Import necessary functions from embedding_utils
# These will now use the config values internally after being updated
from .embedding_utils import get_embedding_client, get_or_create_collection
from typing import List, Dict, Any

def get_top_k(collection: chromadb.Collection, target_text: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieves the top-k most relevant documents from the ChromaDB collection
    based on cosine similarity to the target text.

    Args:
        collection: The ChromaDB collection object to query.
        target_text: The text to find relevant documents for.
        k: The number of top documents to retrieve (0 < k ≤ 100)

    Returns:
        A list of document objects (dictionaries with 'text' and 'metadata'), 
        or an empty list if an error occurs or no documents are found.
    """
    print(f"ChromaDB: Retrieving top {k} documents for target text: {target_text[:min(50, len(target_text))]}...")

    if not target_text:
        raise ValueError("Target text cannot be empty.")
    if not isinstance(k, int) or not (0 < k <= 100):
        raise ValueError("k must be a positive integer and ≤ 100.")

    try:
        results = collection.query(
            query_texts=[target_text], 
            n_results=k,
            include=['documents', 'metadatas']
        )
        documents = results.get('documents', None)[0]
        metadatas = results.get('metadatas', None)[0]
        if not documents:
            raise ValueError("No documents found for target text.")
        documents = [{"text": documents[i], "metadata": metadatas[i]} for i in range(len(documents))]
        return documents

    except Exception as e:
        raise ValueError(f"Error querying collection in get_top_k: {e}")


if __name__ == '__main__':
    print(
        f"Executing '{__file__}' directly. This block is for testing or direct execution.")
    # API_KEY is imported from config and used by get_or_create_collection by default
    print(f"API_KEY is set in config: {bool(API_KEY)}")

    test_client = get_embedding_client()
    test_collection = get_or_create_collection(test_client, api_key=API_KEY)
    collection_count = test_collection.count()
    print(
        f"Test collection '{test_collection.name}' found with {collection_count} items.")
    if collection_count == 0:
        print("Warning (retrieval_utils_test): Collection is empty. Retrieval will likely find no documents.")

    queries_to_test = [
        "What is the nature of subjective experience?",
        "Explain the concept of machine learning.",
        "How can computational complexity be used to understand the limits of human reasoning?",
        "Can creativity be mechanized?",
        "" # Test empty query
    ]
    ks_to_test = [5, 3, 101, 0, 1] # k=101 and k=0 will be corrected by get_top_k

    for i, query in enumerate(queries_to_test):
        k_val = ks_to_test[i]
        print(f"\n--- Test Case {i+1} ---")
        print(f"Querying for: '{query[:50]}...' with k={k_val}")
        
        # Ensure collection is not None before passing to get_top_k
        if test_collection:
            retrieved_docs = get_top_k(test_collection, query, k=k_val)
            if retrieved_docs:
                print(f"Retrieved {len(retrieved_docs)} documents:")
                for doc_idx, doc_obj in enumerate(retrieved_docs):
                    display_doc_snippet = doc_obj.get('text', '')[:min(100, len(doc_obj.get('text', '')))].replace('\n', '')
                    print(
                        f"\tDoc {doc_idx+1}: {display_doc_snippet}...")
            else:
                print("No documents retrieved for this query (or get_top_k returned empty).")
        else:
            print("Skipping query as test_collection is None.")

    print("\nFinished testing retrieval_utils.py.")
