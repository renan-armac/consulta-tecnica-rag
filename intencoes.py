"""Detecção simples de intenções (sem usar o modelo): saudação, agradecimento,
pedido de visão geral do documento e recusa do modelo."""
import re

_SAUDACAO_INICIO = {"oi", "oii", "oiii", "olá", "ola", "eae", "opa", "hey", "hello", "salve",
                    "bom", "boa", "tudo", "td", "e"}
_SAUDACAO_RESTO = {"oi", "oii", "oiii", "olá", "ola", "eae", "opa", "hey", "hello", "salve", "bom",
                   "boa", "dia", "tarde", "noite", "tudo", "td", "bem", "como", "vai", "você",
                   "voce", "vc", "está", "esta", "e", "aí", "ai", "tranquilo", "beleza", "blz",
                   "por", "aqui", "de", "novo"}
_AGRADECIMENTO = {"obrigado", "obrigada", "brigado", "brigada", "valeu", "vlw", "muito", "show",
                  "ok", "certo", "beleza", "blz", "entendi", "perfeito", "legal", "massa", "top",
                  "ótimo", "otimo", "thanks", "grato", "grata", "ajudou", "me", "isso", "demais",
                  "mesmo", "pela", "ajuda", "a", "o", "e"}


def _palavras(texto):
    return re.findall(r"[a-zà-ÿ]+", texto.lower())


def eh_saudacao(texto):
    p = _palavras(texto)
    return bool(p) and len(p) <= 6 and p[0] in _SAUDACAO_INICIO and all(w in _SAUDACAO_RESTO for w in p)


def eh_agradecimento(texto):
    p = _palavras(texto)
    return bool(p) and len(p) <= 6 and all(w in _AGRADECIMENTO for w in p)


_DOC = r"(pdf|documento|arquivo|faq|material|texto)"
_PADROES_VISAO_GERAL = [
    r"principais?\s+(t[óo]picos?|assuntos?|temas?|pontos|se[çc][õo]es)",
    r"principais?\s+informa[çc][õo]es.*\b" + _DOC + r"\b",
    r"\b(t[óo]picos?|temas?|assuntos?)\s+(d[oa]|que)\s+(o\s+|a\s+)?" + _DOC + r"\b",
    r"sobre o que (é|e|trata|fala|explica)\b.*\b" + _DOC + r"\b",
    r"\bo que (tem|cont[ée]m|diz|explica|aborda)\b.*\b" + _DOC + r"\b",
    r"assunto[\s-]*(chave|principal)",
    r"\b(resumo|resumir|resuma)\b.*\b" + _DOC + r"\b",
]


def pede_visao_geral(texto):
    """Perguntas sobre o documento como um todo (tópicos, assunto, resumo)."""
    t = texto.lower()
    return any(re.search(p, t) for p in _PADROES_VISAO_GERAL)


# Verbos que confirmam um pedido de página. Sem eles, frases longas que só
# mencionam "primeira/segunda" (ex.: "a primeira opção do curso") não contam.
_VERBOS_PAGINA = {"ver", "mostra", "mostrar", "mostre", "exibe", "exibir", "conteudo", "conteúdo",
                  "texto", "tem", "diz", "está", "esta", "abre", "abrir", "quero", "queria", "leia",
                  "ler", "traz", "trazer", "fala", "gostaria", "preciso",
                  # verbos de exportação ("gera um PDF da primeira página")
                  "gera", "gerar", "gere", "exporta", "exportar", "exporte", "cria", "criar",
                  "crie", "baixa", "baixar", "salva", "salvar", "manda", "mande", "envia",
                  "enviar", "passa", "passe", "recorta", "recortar", "pdf"}
_PAG = re.compile(r"p[áa]g(?:ina|inas|s?\.)?\s*(\d{1,4})(?:\s*(?:a|at[ée]|-)\s*(\d{1,4}))?(?:\s*e\s*(\d{1,4}))?")

# "primeira página", "segunda e terceira página", "página dois", "última página"...
_ORDINAIS = {"primeir": 1, "segund": 2, "terceir": 3, "quart": 4, "quint": 5, "sext": 6,
             "sétim": 7, "setim": 7, "oitav": 8, "non": 9, "décim": 10, "decim": 10}
_ORD = r"(?:primeir|segund|terceir|quart|quint|sext|s[ée]tim|oitav|non|d[ée]cim)[ao]"
_NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5,
            "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10}
_NUM = r"(?:um|uma|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez)"


def _valor_ordinal(palavra):
    return next(v for k, v in _ORDINAIS.items() if palavra.startswith(k))


def pede_pagina(texto):
    """Páginas pedidas: [3], [1, 2], [-1] (= última). [] se não pediu página.
    Entende 'página 3', 'primeira página', 'páginas 2 a 4', 'página dois',
    'as duas primeiras páginas', 'última página', 'início/final do PDF'."""
    t = texto.lower()
    paginas = []

    m = _PAG.search(t)                                           # página 3 / páginas 2 a 4 / 5 e 7
    if m:
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else None
        paginas += list(range(a, min(b, a + 4) + 1)) if b and b >= a else [a]
        if m.group(3):
            paginas.append(int(m.group(3)))

    m = re.search(r"\b(" + _ORD + r"(?:\s*(?:,|e)\s*" + _ORD + r")*)\s+p[áa]ginas?\b", t)
    if m:                                                        # primeira / segunda e terceira página
        paginas += [_valor_ordinal(w) for w in re.findall(_ORD, m.group(1))]

    m = re.search(r"\b(\d+|" + _NUM + r")\s+primeiras\s+p[áa]ginas?\b", t)
    if m:                                                        # as duas primeiras páginas
        n = int(m.group(1)) if m.group(1).isdigit() else _NUMEROS[m.group(1).replace("três", "três")]
        paginas += list(range(1, min(n, 5) + 1))

    m = re.search(r"\bp[áa]ginas?\s+(" + _NUM + r")\b", t)       # página dois
    if m:
        paginas.append(_NUMEROS[m.group(1)])

    if re.search(r"\b[úu]ltima\s+p[áa]gina\b|\b(fim|final)\s+d[oa]\s+(pdf|documento|arquivo)\b", t):
        paginas.append(-1)
    if re.search(r"\b(in[ií]cio|come[çc]o)\s+d[oa]\s+(pdf|documento|arquivo)\b", t):
        paginas.append(1)

    if not paginas:
        return []
    palavras = re.findall(r"[a-zà-ÿ]+", t)
    if len(palavras) > 5 and not (_VERBOS_PAGINA & set(palavras)):
        return []
    positivas = sorted({p for p in paginas if p > 0})[:5]
    return positivas + ([-1] if -1 in paginas else [])


def pede_fonte(texto):
    """'quero ver o conteúdo da fonte' / 'mostra as fontes'."""
    t = texto.lower()
    return bool(
        re.search(r"\b(conte[úu]do|texto|trecho)s?\s+(d[aeo]s?\s+)?fontes?\b", t)
        or re.search(r"\b(ver|mostr\w*|abr\w*)\b.{0,30}\bfontes?\b", t)
    )


def eh_recusa(resposta, mensagem_padrao):
    """True se o modelo se recusou (frase padrão, mesmo incompleta, ou pedido de desculpas)."""
    r = resposta.strip().lower()
    curto = mensagem_padrao.split("(")[0].strip().lower()   # 'ai tem que abrir o pop'
    return (bool(curto) and curto in r) or bool(
        re.match(r"^(desculpe|sinto muito|lamento|n[ãa]o (posso|consigo))", r)
    )
