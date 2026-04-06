from .qdrant import doc_store
from .embeddings import get_text_embedder, get_doc_embedder, unload_embedders
from .rag import get_rag_pipeline, get_indexing_pipeline
from .llm import get_llm_component
from .embedder_pool import get_embedder, unload_embedder, unload_all_embedders, get_pool_stats
from .cache_service import get_cached, set_cached, clear_cache, cache_size
from .chat_service import handle_chat_completions, handle_code_query, handle_query
from .retrieval_service import retrieve_rag, retrieve_web
from .prompt_service import build_rag_prompt, build_query_prompt, build_code_prompt, merge_context

__all__ = [
    "doc_store",
    "get_text_embedder",
    "get_doc_embedder",
    "unload_embedders",
    "get_rag_pipeline",
    "get_indexing_pipeline",
    "get_llm_component",
    "get_embedder",
    "unload_embedder",
    "unload_all_embedders",
    "get_pool_stats",
    "get_cached",
    "set_cached",
    "clear_cache",
    "cache_size",
    "handle_chat_completions",
    "handle_code_query",
    "handle_query",
    "retrieve_rag",
    "retrieve_web",
    "build_rag_prompt",
    "build_query_prompt",
    "build_code_prompt",
    "merge_context",
]
