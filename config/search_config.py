"""
Configuración centralizada para Azure AI Search
"""

# Chunking configuration
CHUNK_SIZE = 1024  # tokens (increased from 512 for Phase 1)
CHUNK_OVERLAP = 512  # tokens (50% overlap - increased from 128/25%)

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 16  # Process 16 chunks at a time

# Index configuration
INDEX_NAME = "contratos-rocka-index"
VECTOR_PROFILE = "vector-config"
SEMANTIC_CONFIG = "semantic-config"

# Search configuration
TOP_K = 5  # Return top 5 results
QUERY_TYPE = "vector_semantic_hybrid"  # Best for RAG

# Spanish analyzer
SPANISH_ANALYZER = "es.microsoft"
