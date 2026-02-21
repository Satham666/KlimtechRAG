from .rag import rag_pipeline


def get_llm_component():
    return rag_pipeline.get_component("llm")
