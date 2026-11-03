# Clean architecture

The domain depends on no framework. Use cases only know ports, interfaces such as
VectorStore or TextGenerator. Adapters (ChromaDB, OpenAI, Mistral, Anthropic,
Ollama) live in the infrastructure layer and are selected by configuration.
A unit test of a use case relies on in-memory fakes: no network, no model.

# Reducing hallucinations

When no passage exceeds the relevance threshold, the system says so instead of
inventing an answer. Every answer cites its sources with their similarity score.
