# LangGraph

LangGraph is a library that models an agent workflow as a graph of states.
Each node is a function that reads the state and updates it; conditional edges
decide which node runs next. This makes loops possible (for example rewriting a
query and searching again) that linear chains cannot express.

# Semantic search

Semantic search compares the meaning of a question with the meaning of passages
using embeddings: vectors where two sentences with similar meaning are close in
cosine distance, even when they share no word. ChromaDB stores these vectors and
finds the nearest ones.
