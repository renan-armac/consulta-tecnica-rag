"""Núcleo do RAG: busca nos documentos + geração da resposta.
Usado pelo chat visual (app.py) e pelo terminal (main.py).
Todas as configurações ficam aqui."""
import re
from dataclasses import dataclass, field
from typing import Optional

from langchain_chroma.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from embeddings import criar_embeddings
from intencoes import (eh_agradecimento, eh_saudacao, pede_fonte, pede_pagina, pede_visao_geral,
                       eh_recusa as _eh_recusa)
from leitor_pdf import carregar_documentos
from topicos import extrair_topicos, formatar_visao_geral

# ---------------- Configurações (ajuste aqui) ----------------
PASTA_BASE = "base"
CAMINHO_DB = "db"
MODELO_LLM = "llama3.2:3b"      # menor e mais rápido. Para mais qualidade: "llama3.1:8b" ou "qwen2.5:7b"
K_RESULTADOS = 3                # quantos trechos enviar ao modelo
LIMITE_RELEVANCIA = 0.6         # abaixo disso a pergunta é considerada fora do tema
MOSTRAR_SCORES = True           # mostra os scores para você calibrar o limite
MENSAGEM_FORA_DO_TEMA = "Ai tem que abrir o pop (Problema de Outra Pessoa)"
TURNOS_DE_MEMORIA = 6           # quantas mensagens recentes o modelo "lembra"
# -------------------------------------------------------------

PROMPT_RESPOSTA = """Você é um assistente que responde em português do Brasil, de forma clara, natural e direta, usando SOMENTE o contexto abaixo.
- Use as informações do contexto para responder e não invente nada que não esteja nele.
- Só se o contexto não tiver nenhuma informação relacionada à pergunta, responda exatamente: """ + MENSAGEM_FORA_DO_TEMA + """
- Nunca peça desculpas nem diga que não pode responder.

Histórico da conversa (use apenas para entender do que a pergunta fala):
{historico}

Contexto:
{base_conhecimento}

Pergunta: {pergunta}
Resposta:"""

PROMPT_VISAO_GERAL = """Com base nos trechos do documento abaixo, liste em português do Brasil os principais assuntos que ele aborda, em tópicos curtos (um por linha, começando com "- ").

Trechos:
{base_conhecimento}

Principais assuntos:"""

PROMPT_REFORMULAR = """Reescreva a "Nova pergunta" para que ela seja compreensível sozinha, usando a conversa só se a pergunta depender dela (por exemplo, quando usa "ele", "isso", "e o outro?").
Não invente assuntos. Se a pergunta já for compreensível, repita-a igual.
Responda apenas com a pergunta reescrita, sem explicações.

Conversa:
{historico}

Nova pergunta: {pergunta}
Pergunta reescrita:"""


@dataclass
class Recursos:
    db: Chroma
    modelo: ChatOllama
    topicos: dict = field(default_factory=dict)   # {arquivo: [{'titulo','pagina'}]}
    arquivos: list = field(default_factory=list)  # nomes dos PDFs da pasta base
    paginas: dict = field(default_factory=dict)   # {arquivo: {n_da_pagina: texto}}


@dataclass
class Preparo:
    fora_do_tema: bool
    resultados: list = field(default_factory=list)
    pergunta_busca: str = ""
    scores: list = field(default_factory=list)
    modo: str = "normal"                # normal | fora_do_tema | conversa | visao_geral
    texto_fixo: Optional[str] = None    # resposta pronta (sem chamar o modelo)
    prompt: str = "normal"              # normal | visao
    fontes: list = field(default_factory=list)
    titulo: Optional[str] = None        # título do PDF, quando não for a própria pergunta


def carregar_recursos():
    """Carrega banco, modelo e a lista de tópicos dos PDFs (uma única vez)."""
    db = Chroma(persist_directory=CAMINHO_DB, embedding_function=criar_embeddings())
    modelo = ChatOllama(model=MODELO_LLM, temperature=0, keep_alive="30m")
    documentos = carregar_documentos(PASTA_BASE)
    arquivos = sorted({str(d.metadata["source"]).replace("\\", "/").split("/")[-1] for d in documentos})
    paginas = {}
    for d in documentos:
        nome = str(d.metadata["source"]).replace("\\", "/").split("/")[-1]
        paginas.setdefault(nome, {})[int(d.metadata["page"]) + 1] = d.page_content
    return Recursos(db=db, modelo=modelo, topicos=extrair_topicos(documentos),
                    arquivos=arquivos, paginas=paginas)


def eh_recusa(resposta):
    return _eh_recusa(resposta, MENSAGEM_FORA_DO_TEMA)


def formatar_historico(mensagens, limite=TURNOS_DE_MEMORIA):
    """Converte as últimas mensagens válidas em texto para o prompt."""
    validas = [m for m in mensagens if m.get("tipo") in ("pergunta", "resposta")]
    linhas = []
    for m in validas[-limite:]:
        quem = "Usuário" if m["role"] == "user" else "Assistente"
        linhas.append(f"{quem}: {m['content'][:600]}")
    return "\n".join(linhas) if linhas else "(início da conversa)"


def _buscar(recursos, pergunta):
    resultados = recursos.db.similarity_search_with_relevance_scores(pergunta, k=K_RESULTADOS)
    melhor = resultados[0][1] if resultados else 0.0
    return resultados, melhor


def _reformular(recursos, pergunta, historico):
    try:
        prompt = PROMPT_REFORMULAR.format(historico=historico, pergunta=pergunta)
        texto = recursos.modelo.invoke(prompt).content.strip().strip('"')
        return texto or pergunta
    except Exception:
        return pergunta


def _nomes(recursos):
    return ", ".join(f"*{a}*" for a in recursos.arquivos) or "os documentos carregados"


def _alvos_das_fontes(mensagens):
    """Páginas citadas na última resposta: [(arquivo, pagina), ...]."""
    for m in reversed(mensagens):
        if m.get("tipo") == "resposta" and m.get("fontes"):
            alvos = []
            for f in m["fontes"]:
                achou = re.match(r"^(.*?)\s*\(pág\.\s*(\d+)\)$", f)
                if achou:
                    alvos.append((achou.group(1), int(achou.group(2))))
            return sorted(set(alvos), key=lambda x: (x[0], x[1]))[:3]
    return []


def _mostrar_paginas(recursos, alvos, titulo):
    """Texto exato das páginas pedidas (sem usar o modelo)."""
    blocos, fontes = [], []
    for arquivo, pag in alvos:
        for nome in ([arquivo] if arquivo else list(recursos.paginas)):
            paginas_do_arquivo = recursos.paginas.get(nome, {})
            n = max(paginas_do_arquivo) if (pag == -1 and paginas_do_arquivo) else pag  # -1 = última
            texto = paginas_do_arquivo.get(n)
            if texto:
                texto = re.sub(r"(?<!\n)\n(?!\n)", "  \n", texto)   # preserva as quebras de linha
                blocos.append(f"📄 **{nome} - página {n}**\n\n{texto}")
                fontes.append(f"{nome} (pág. {n})")
    if not blocos:
        total = ", ".join(f"{n} tem {len(p)} páginas" for n, p in recursos.paginas.items())
        return Preparo(False, modo="conversa",
                       texto_fixo=f"Não encontrei essa página. ({total or 'nenhum documento carregado'})")
    return Preparo(False, modo="pagina", texto_fixo="\n\n---\n\n".join(blocos),
                   fontes=fontes, titulo=titulo)


def _visao_geral(recursos):
    """Resposta para 'quais os tópicos do PDF?': usa os títulos do próprio documento."""
    if recursos.topicos:
        return Preparo(False, modo="visao_geral", texto_fixo=formatar_visao_geral(recursos.topicos),
                       fontes=list(recursos.topicos))
    # PDF sem títulos numerados: o modelo resume trechos espalhados pelo documento
    dados = recursos.db.get(include=["documents", "metadatas"])
    docs, metas = dados.get("documents", []), dados.get("metadatas", [])
    passo = max(1, len(docs) // 6)
    amostra = [(Document(page_content=docs[i], metadata=metas[i] or {}), 1.0)
               for i in range(0, len(docs), passo)][:6]
    return Preparo(False, resultados=amostra, modo="visao_geral", prompt="visao",
                   pergunta_busca="principais assuntos do documento")


def preparar(recursos, pergunta, mensagens):
    """Decide o que fazer com a pergunta.

    1) Saudação / agradecimento -> resposta pronta.
    2) Pergunta sobre o documento todo (tópicos, assunto, resumo) -> visão geral.
    3) Pergunta sobre uma página ("conteúdo da página 3") ou sobre as fontes da última
       resposta -> mostra o texto exato, sem o modelo.
    4) Pergunta normal: busca nos documentos; se o melhor trecho não passar do
       limite, é fora do tema. Perguntas curtas que parecem continuação ("e o
       segundo?") são reescritas com a conversa antes de uma segunda tentativa.
    """
    if eh_saudacao(pergunta):
        return Preparo(False, modo="conversa", texto_fixo=(
            f"Olá! 👋 Posso responder perguntas sobre {_nomes(recursos)}. "
            "Pergunte o que quiser, peça os *principais tópicos do PDF* "
            "ou diga *gera um PDF disso* para receber a resposta em PDF."))
    if eh_agradecimento(pergunta):
        return Preparo(False, modo="conversa",
                       texto_fixo="Por nada! Se precisar de mais alguma coisa, é só perguntar. 🙂")
    paginas = pede_pagina(pergunta)
    if paginas:
        if paginas == [-1]:
            rotulo = "última página"
        elif len(paginas) == 1:
            rotulo = f"página {paginas[0]}"
        else:
            rotulo = "páginas " + ", ".join("última" if n == -1 else str(n) for n in paginas)
        return _mostrar_paginas(recursos, [(None, n) for n in paginas], f"Conteúdo da {rotulo}")
    if pede_fonte(pergunta):
        alvos = _alvos_das_fontes(mensagens)
        if not alvos:
            return Preparo(False, modo="conversa",
                           texto_fixo="Ainda não há fontes para mostrar. Faça uma pergunta primeiro.")
        return _mostrar_paginas(recursos, alvos, "Conteúdo das fontes")
    if pede_visao_geral(pergunta):
        return _visao_geral(recursos)

    resultados, melhor = _buscar(recursos, pergunta)
    scores = [round(r[1], 3) for r in resultados]
    if melhor >= LIMITE_RELEVANCIA:
        return Preparo(False, resultados, pergunta, scores)

    historico = formatar_historico(mensagens)
    if historico != "(início da conversa)" and len(pergunta.split()) <= 8:
        reescrita = _reformular(recursos, pergunta, historico)
        if reescrita != pergunta:
            resultados2, melhor2 = _buscar(recursos, reescrita)
            scores = [round(r[1], 3) for r in resultados2]
            if melhor2 >= LIMITE_RELEVANCIA:
                return Preparo(False, resultados2, reescrita, scores)

    return Preparo(True, resultados, pergunta, scores, modo="fora_do_tema")


def gerar_stream(recursos, pergunta, preparo, mensagens):
    """Gera a resposta aos poucos (generator de texto)."""
    if preparo.texto_fixo:
        yield preparo.texto_fixo
        return
    base = "\n\n----\n\n".join(r[0].page_content for r in preparo.resultados)
    if preparo.prompt == "visao":
        prompt = ChatPromptTemplate.from_template(PROMPT_VISAO_GERAL).invoke(
            {"base_conhecimento": base})
    else:
        prompt = ChatPromptTemplate.from_template(PROMPT_RESPOSTA).invoke(
            {"historico": formatar_historico(mensagens),
             "base_conhecimento": base,
             "pergunta": pergunta})
    for pedaco in recursos.modelo.stream(prompt):
        yield pedaco.content


def listar_fontes(resultados):
    """Ex.: ['FAQ Python Video YouTube.pdf (pág. 3)']"""
    fontes = []
    for doc, _ in resultados:
        meta = doc.metadata or {}
        nome = str(meta.get("source", "documento")).replace("\\", "/").split("/")[-1]
        pagina = meta.get("page")
        item = f"{nome} (pág. {int(pagina) + 1})" if pagina is not None else nome
        if item not in fontes:
            fontes.append(item)
    return fontes
