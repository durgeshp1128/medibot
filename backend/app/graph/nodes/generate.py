from typing import List, Dict, Any
from backend.app.graph.state import AgentState
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv() 

SYSTEM_PROMPT = "You are MediBot, an internal medical assistant. Use the provided retrieved chunks to answer the user's question. Cite source_document and section_title for each chunk used. Be concise and factual."

def generate_node(state: AgentState) -> AgentState:
    """Generate answer using LLM.
    Expects `state["question"]` and `state["retrieved_chunks"]` (list of dicts with text, source_document, section_title).
    Returns `final_answer`, `sources`, and `retrieval_type`.
    """
    question = state.get("question", "")
    chunks = state.get("retrieved_chunks", [])
    # Build context from top chunks
    context = "\n\n".join([f"Chunk {i+1}: {c.get('text', '')}" for i, c in enumerate(chunks)])
    prompt = f"Question: {question}\n\nContext:\n{context}\n\nAnswer the question using only the above information. Provide citations in the format [source_document - section_title]."

    try:
        # response = openai.ChatCompletion.create(
        #     model=os.getenv("OPENAI_CHAT_MODEL", "gpt-3.5-turbo"),
        #     messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        #     temperature=0.0,
        # )
        # answer = response["choices"][0]["message"]["content"].strip()
        llm = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        response = llm.invoke(prompt)
        answer = response.content.strip()
    except Exception as e:
        answer = f"Error generating answer: {e}"

    # Extract sources from chunks
    sources = [
        {"source_document": c.get("source_document", ""), "section_title": c.get("section_title", ""), "collection": c.get("collection", "")}
        for c in chunks
    ]
    state["final_answer"] = answer
    state["sources"] = sources
    state["retrieval_type"] = "hybrid_rag"
    return state