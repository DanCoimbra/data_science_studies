def create_summarization_prompt(retrieved_docs: list[str], user_prompt: str) -> str:
    """
    Creates a prompt for the LLM to summarize information from retrieved documents 
    that is relevant to the topics mentioned in the user's prompt.

    Args:
        retrieved_docs: A list of strings, where each string is a document snippet.
        user_prompt: The original prompt from the user, whose contents implicitly indicate the topics of interest.

    Returns:
        A formatted prompt string for summarization.
    """

    if not retrieved_docs:
        # Fallback if no documents are retrieved, though ideally the orchestrator handles this.
        return f"User prompt: '{user_prompt}'. No relevant documents were found to summarize as relevant to this prompt."

    formatted_documents = "\n\n---\n\n".join(retrieved_docs)

    prompt = f"""
User Prompt (Topics of Interest): "{user_prompt}"

Retrieved Documents:
---
{formatted_documents}
---

Please review the User Prompt to understand the topics of interest.
Then, based *only* on the information contained in the Retrieved Documents, provide a concise summary of the key points from the documents that are relevant to those topics.
Do not attempt to answer any questions that might be implied in the prompt; focus solely on summarizing the relevant information found in the documents.
If the documents do not contain information relevant to the topics in the User Prompt, please state that.
Do not include information not present in the provided documents.
However, do mention interesting research leads one could pursue based on the documents.
"""
    return prompt


def create_evaluation_prompt(user_prompt: str, retrieved_docs: list[str]) -> str:
    """
    Creates a prompt for the LLM to evaluate ideas in a prompt.

    Args:
        user_prompt: The original prompt from the user.
        retrieved_docs: The list of document snippets used for the summary.

    Returns:
        A formatted prompt string for evaluation.
    """

    formatted_documents = "\n\n---\n\n".join(retrieved_docs)

    prompt_text = f"""
Original User Prompt: "{user_prompt}"

Retrieved Documents:
---
{formatted_documents}
---

Based on the Original User Prompt and the Retrieved Documents, please evaluate the ideas or statements presented in the user's prompt. Consider the following aspects:

1.  Plausibility/Support: Are the ideas in the user's prompt supported or contradicted by the information in the retrieved documents?
2.  Nuance/Complexity: Do the retrieved documents add any nuance, complexity, or alternative perspectives to the user's prompt?
3.  Correctness/Accuracy: Are factual statements in the user's prompt accurate in light of the retrieved documents?
4.  Background knowledge: Irrespective of the documents' contents, is the user's prompt lacking in plausibility, correctness,or nuance?

Please provide a concise analysis based on these points, drawing only from the provided documents.
If the documents are not sufficient to help evaluate the prompt, please state that.
However, carry out the 'Background knowledge' check even if the documents are lacking in information.
"""
    return prompt_text


if __name__ == '__main__':
    print(f"Testing prompt_templates.py...")

    # Imports for ChromaDB and querying - these will use config internally
    from socratic_agent.rag.embedding_utils import get_embedding_client, get_or_create_collection
    from socratic_agent.rag.retrieval_utils import get_top_k
    # Import API_KEY from config to check its status for the test, though rag utils handle it for ops
    from socratic_agent.core.config import API_KEY 

    if not API_KEY:
        # This warning is now mainly for the test script's awareness.
        # The actual embedding/retrieval functions will default based on config.
        print("Warning (prompt_templates_test): GOOGLE_API_KEY not found in config."
              " ChromaDB might use default embeddings.")
    else:
        print(f"Info (prompt_templates_test): GOOGLE_API_KEY found in config.")

    test_client = get_embedding_client()
    if not test_client:
        print("Error (prompt_templates_test): Failed to get ChromaDB client. Aborting tests.")
        exit()

    # get_or_create_collection uses API_KEY from config by default
    test_collection = get_or_create_collection(test_client)
    if not test_collection:
        print(
            f"Error (prompt_templates_test): Failed to get or create collection. Aborting tests.")
        exit()

    collection_count = test_collection.count()
    print(
        f"Test collection '{test_collection.name}' found with {collection_count} items.")
    if collection_count == 0:
        print("Warning (prompt_templates_test): The collection is empty. Document retrieval will not find any documents.")

    user_prompts_to_test = [
        "Rainforest realism is a plausible reductionist paradigm that accounts for emergence.",
        "Ontological relationalism is a general but at least semi-formal philosophical framework.",
        "Ethical anti-realism is a tenable position for a physicalist with an externalist epistemology.",
    ]
    k_for_retrieval = 5

    for i, current_prompt in enumerate(user_prompts_to_test):
        print(f"\n--- Test Iteration {i+1} ---")
        print(f"User Prompt: '{current_prompt}'")

        print(f"\nAttempting to retrieve top-{k_for_retrieval} documents...")
        retrieved_docs = get_top_k(test_collection, current_prompt, k=k_for_retrieval)

        if retrieved_docs:
            print(f"Retrieved {len(retrieved_docs)} documents:")
        else:
            print("No documents retrieved for this prompt.")

        # Test Summarization Prompt
        print("\n--- Generated Summarization Prompt ---")
        summarization_prompt = create_summarization_prompt(
            retrieved_docs, current_prompt)
        print(summarization_prompt)

        # Test Evaluation Prompt
        print("\n--- Generated Evaluation Prompt ---")
        evaluation_prompt = create_evaluation_prompt(
            current_prompt, retrieved_docs)  # Corrected order of arguments
        print(evaluation_prompt)

        print("\n--- End of Test Iteration ---")

    print("\nFinished testing prompt_templates.py.")
