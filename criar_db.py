from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma.vectorstores import Chroma

from embeddings import criar_embeddings
from leitor_pdf import carregar_documentos as ler_pdfs

PASTA_BASE = "base"
PASTA_DB = "db"

# Trechos maiores o suficiente para manter pergunta + resposta juntas
TAMANHO_CHUNK = 2000
SOBREPOSICAO = 500


def criar_db():
    documentos = carregar_documentos()

    if not documentos:
        print("Nenhum PDF encontrado na pasta base.")
        return

    chunks = dividir_chunks(documentos)
    vetorizar_chunks(chunks)


def carregar_documentos():
    documentos = ler_pdfs(PASTA_BASE)
    print(f"Páginas carregadas: {len(documentos)}")
    return documentos


def dividir_chunks(documentos):
    separador = RecursiveCharacterTextSplitter(
        chunk_size=TAMANHO_CHUNK,
        chunk_overlap=SOBREPOSICAO,
        add_start_index=True,
    )
    chunks = separador.split_documents(documentos)
    print(f"Total de chunks gerados: {len(chunks)}")
    return chunks


def vetorizar_chunks(chunks):
    embeddings = criar_embeddings()

    # Apaga a coleção antiga (evita duplicatas e métricas antigas)
    try:
        Chroma(persist_directory=PASTA_DB, embedding_function=embeddings).delete_collection()
    except Exception:
        pass

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PASTA_DB,
        collection_metadata={"hnsw:space": "cosine"},  # similaridade por cosseno
    )
    print("Banco de dados vetorial criado com sucesso!")


if __name__ == "__main__":
    criar_db()
