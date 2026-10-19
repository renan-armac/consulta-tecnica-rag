"""Leitura de PDFs com texto limpo (substitui o PyPDFDirectoryLoader).

O leitor padrão extrai alguns PDFs com uma palavra por linha, o que
estraga os trechos usados na busca. Aqui usamos o modo 'layout' do pypdf
e limpamos o texto."""
import re
from pathlib import Path

import pypdf
from langchain_core.documents import Document


def _limpar_texto(texto):
    texto = re.sub(r"[​‌‍﻿]", "", texto)               # invisíveis
    texto = re.sub(r"[-\U000f0000-\U0010ffff]", "", texto)     # símbolos sem fonte
    linhas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.splitlines()]
    texto = "\n".join(linhas)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _texto_da_pagina(pagina):
    try:
        return _limpar_texto(pagina.extract_text(extraction_mode="layout") or "")
    except Exception:
        # pypdf antigo: sem modo layout. Junta tudo em um parágrafo contínuo.
        bruto = _limpar_texto(pagina.extract_text() or "")
        return re.sub(r"\s+", " ", bruto)


def carregar_documentos(pasta="base"):
    """Retorna uma lista de Document (um por página) com metadata source/page."""
    documentos = []
    for caminho in sorted(Path(pasta).glob("*.pdf")):
        try:
            leitor = pypdf.PdfReader(str(caminho))
            for numero, pagina in enumerate(leitor.pages):
                texto = _texto_da_pagina(pagina)
                if texto:
                    documentos.append(
                        Document(page_content=texto,
                                 metadata={"source": str(caminho), "page": numero})
                    )
        except Exception as erro:
            print(f"Não consegui ler {caminho.name}: {erro}")
    return documentos
