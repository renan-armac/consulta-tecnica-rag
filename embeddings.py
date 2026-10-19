from langchain_ollama import OllamaEmbeddings


class NomicEmbeddings(OllamaEmbeddings):
    """O nomic-embed-text funciona melhor quando textos e perguntas
    recebem prefixos diferentes."""

    def embed_documents(self, texts):
        return super().embed_documents(["search_document: " + t for t in texts])

    def embed_query(self, text):
        return super().embed_query("search_query: " + text)


def criar_embeddings():
    return NomicEmbeddings(model="nomic-embed-text")
