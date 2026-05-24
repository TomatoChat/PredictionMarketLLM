# Dimension of the embedding vectors stored in MARKETS. Must match the
# output dimension of the embedding model used by the llm service
# (text-embedding-3-large = 3072). Kept hardcoded here to avoid a back-import
# from the llm service into this shared library.
EMBEDDING_DIMS = 3072
