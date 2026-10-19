"""Descobre os tópicos (títulos numerados) dos PDFs e monta a visão geral."""
import re
from collections import Counter, defaultdict

_TITULO = re.compile(r"^(\d{1,2})\s*[.)]\s+(\S.*)$")
ACRONIMOS = {"HTML", "CSS", "JS", "IDE", "SQL", "API", "IA", "PDF"}


def _proporcao_maiuscula(texto):
    letras = [c for c in texto if c.isalpha()]
    return sum(c.isupper() for c in letras) / len(letras) if letras else 0.0


def _vocabulario(documentos):
    """Palavras que no corpo do texto aparecem com inicial maiúscula (Python, Django...)."""
    texto = "\n".join(d.page_content for d in documentos)
    cap = Counter(w.lower() for w in re.findall(r"\b[A-ZÀ-Ý][a-zà-ÿ]{2,}\b", texto))
    baixa = Counter(re.findall(r"\b[a-zà-ÿ]{3,}\b", texto))
    return {w: w.capitalize() for w, n in cap.items() if n > baixa.get(w, 0)}


def _embelezar(titulo, vocab):
    """'TENHO INTERESSE NO PYTHON' -> 'Tenho interesse no Python'."""
    titulo = titulo.strip(" \t“”\"':;")

    def troca(m):
        tok = m.group(0)
        if tok.lower() in vocab:
            return vocab[tok.lower()]
        if tok in ACRONIMOS:
            return tok
        return tok.lower()

    t = re.sub(r"[A-Za-zÀ-ÿ]+", troca, titulo)
    return t[:1].upper() + t[1:] if t else t


def extrair_topicos(documentos):
    """Retorna {arquivo: [{'titulo','pagina'}, ...]}. Vazio se o PDF não tiver títulos numerados."""
    vocab = _vocabulario(documentos)
    por_arquivo = defaultdict(list)
    vistos = defaultdict(set)

    for doc in documentos:
        arquivo = str(doc.metadata.get("source", "documento")).replace("\\", "/").split("/")[-1]
        pagina = int(doc.metadata.get("page", 0)) + 1
        linhas = doc.page_content.splitlines()
        i = 0
        while i < len(linhas):
            m = _TITULO.match(linhas[i])
            if m and _proporcao_maiuscula(m.group(2)) >= 0.7 and m.group(1) not in vistos[arquivo]:
                titulo, j = m.group(2), i + 1
                # título que continua na linha seguinte (também em maiúsculas)
                while j < len(linhas):
                    prox = linhas[j]
                    if (prox and _proporcao_maiuscula(prox) >= 0.7 and not _TITULO.match(prox)
                            and not prox.upper().startswith("PARTE")):
                        titulo += " " + prox
                        j += 1
                    else:
                        break
                vistos[arquivo].add(m.group(1))
                por_arquivo[arquivo].append(
                    {"titulo": _embelezar(re.sub(r"\s+", " ", titulo), vocab), "pagina": pagina}
                )
                i = j
            else:
                i += 1

    # só vale como "lista de tópicos" se achou uma quantidade razoável
    return {a: t for a, t in por_arquivo.items() if len(t) >= 3}


def formatar_visao_geral(topicos_por_arquivo):
    blocos = []
    for arquivo, topicos in topicos_por_arquivo.items():
        linhas = [f"📄 **{arquivo}** tem {len(topicos)} tópicos:", ""]
        for n, t in enumerate(topicos, 1):
            linhas.append(f"{n}. {t['titulo']} (pág. {t['pagina']})")
        blocos.append("\n".join(linhas))
    rodape = (
        "\n\nQuer saber mais sobre algum deles? É só perguntar. "
        "Se quiser, peça também: *gera um PDF disso*."
    )
    return "\n\n".join(blocos) + rodape
