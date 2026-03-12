import logging

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator

from ..config import settings
from .qdrant import doc_store
from .embeddings import text_embedder, doc_embedder

logger = logging.getLogger("klimtechrag")

indexing_pipeline = Pipeline()
indexing_pipeline.add_component(
    "splitter", DocumentSplitter(split_by="word", split_length=200, split_overlap=30)
)
indexing_pipeline.add_component("embedder", doc_embedder)
indexing_pipeline.add_component(
    "writer", DocumentWriter(document_store=doc_store, policy=DuplicatePolicy.OVERWRITE)
)
indexing_pipeline.connect("splitter", "embedder")
indexing_pipeline.connect("embedder", "writer")

rag_pipeline = Pipeline()
rag_pipeline.add_component("embedder", text_embedder)
rag_pipeline.add_component(
    "retriever", QdrantEmbeddingRetriever(document_store=doc_store, top_k=5)
)
rag_pipeline.add_component(
    "prompt_builder",
    PromptBuilder(
        template="Given these documents:\n{% for doc in documents %}\n{{ doc.content }}\n{% endfor %}\n\nAnswer: {{query}}",
        required_variables=["documents", "query"],
    ),
)
rag_pipeline.add_component("llm", OpenAIGenerator(model=settings.llm_model_name))
rag_pipeline.connect("embedder", "retriever")
rag_pipeline.connect("retriever", "prompt_builder.documents")
rag_pipeline.connect("prompt_builder", "llm")
