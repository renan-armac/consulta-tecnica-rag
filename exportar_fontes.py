"""
Exportar as PÁGINAS ORIGINAIS da base como PDF.
=================================================

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Existem duas formas MUITO diferentes de entregar um PDF ao usuário:

1) PDF GERADO (arquivo `pdf_utils.py`)
   Pegamos o TEXTO da resposta da IA e desenhamos um PDF novo, do zero,
   com a biblioteca `fpdf`. É um documento novo, com a nossa formatação.
   Serve para: "gera um PDF dessa resposta".

2) PDF RECORTADO (este arquivo)
   NÃO criamos nada novo. Abrimos o PDF original que está na pasta `base/`
   e copiamos as páginas inteiras (ex.: a 1 e a 5) para um PDF novo.
   O resultado é IDÊNTICO ao original: mesma fonte, mesmas cores, emojis,
   imagens e tabelas — porque são literalmente as mesmas páginas.
   Serve para: "quero o PDF da fonte / da base / de onde você tirou isso".

A diferença prática: no caso 1 o conteúdo passou pela IA e foi reescrito;
no caso 2 o usuário recebe a prova original, sem nenhuma interferência.

COMO FUNCIONA O RECORTE (a parte que importa aprender)
------------------------------------------------------
A biblioteca `pypdf` trabalha com dois objetos:

    PdfReader  -> abre um PDF existente e dá acesso à lista `.pages`
    PdfWriter  -> monta um PDF novo em memória, recebendo páginas

O recorte é basicamente isto:

    leitor = PdfReader("base/arquivo.pdf")
    escritor = PdfWriter()
    escritor.add_page(leitor.pages[0])   # página 1 (a lista começa em 0!)
    escritor.add_page(leitor.pages[4])   # página 5
    escritor.write(buffer)

ATENÇÃO AO ÍNDICE: para o ser humano a primeira página é a "página 1";
para o Python ela é `pages[0]`. Por isso aparece `numero - 1` no código.

FLUXO COMPLETO DENTRO DO APP
----------------------------
    Usuário: "quero o PDF da fonte"
        |
        v
    pede_pdf_de_origem(texto)  -> confirma que é este tipo de pedido
        |
        v
    mapa_das_fontes(fontes)    -> le ["FAQ.pdf (pág. 1)", "FAQ.pdf (pág. 5)"]
                                  e devolve {"FAQ.pdf": [1, 5]}
        |
        v
    recortar_paginas(mapa, "base")  -> devolve os bytes do PDF final
        |
        v
    st.download_button(...)    -> o usuário baixa o arquivo
"""
import io
import re

import pypdf

# ---------------------------------------------------------------------------
# PARTE 1 - Entender o PEDIDO do usuário
# ---------------------------------------------------------------------------

# Palavras que indicam que o usuário quer o material ORIGINAL, e não um
# resumo escrito pela IA. Se qualquer uma aparecer no pedido de PDF, usamos
# o recorte em vez da geração de texto.
_PALAVRAS_DE_ORIGEM = (
    r"fonte|fontes|base|original|originais|documento original|"
    r"p[áa]gina|p[áa]ginas|trecho|trechos|de onde|da onde|onde (voc[êe] )?tirou|"
    r"material|refer[êe]ncia|refer[êe]ncias"
)


def pede_pdf_de_origem(texto):
    """O usuário quer o PDF com as PÁGINAS ORIGINAIS da base?

    Esta função só é chamada DEPOIS que `pdf_utils.pediu_pdf()` já confirmou
    que existe um pedido de PDF. Aqui decidimos apenas QUAL tipo de PDF.

    >>> pede_pdf_de_origem("quero o pdf da fonte")
    True
    >>> pede_pdf_de_origem("exporta o pdf das páginas que você usou")
    True
    >>> pede_pdf_de_origem("gera um pdf dessa resposta")
    False
    """
    return bool(re.search(_PALAVRAS_DE_ORIGEM, texto.lower()))


# ---------------------------------------------------------------------------
# PARTE 2 - Descobrir QUAIS páginas de QUAIS arquivos exportar
# ---------------------------------------------------------------------------

# As fontes são guardadas como texto, no formato "arquivo.pdf (pág. 5)".
# Esta expressão regular separa o nome do arquivo do número da página:
#   grupo 1 = "FAQ Python Video YouTube.pdf"
#   grupo 2 = "5"
_FORMATO_DA_FONTE = re.compile(r"^(.*?)\s*\(pág\.\s*(\d+)\)$")


def mapa_das_fontes(fontes):
    """Converte a lista de fontes de uma resposta em {arquivo: [páginas]}.

    Entrada:  ["FAQ.pdf (pág. 5)", "FAQ.pdf (pág. 1)", "Outro.pdf (pág. 2)"]
    Saída:    {"FAQ.pdf": [1, 5], "Outro.pdf": [2]}

    As páginas saem ordenadas e sem repetição, para o PDF final ficar na
    ordem natural de leitura.
    """
    mapa = {}
    for fonte in fontes or []:
        encontrado = _FORMATO_DA_FONTE.match(fonte)
        if encontrado:
            arquivo = encontrado.group(1)
            pagina = int(encontrado.group(2))
            mapa.setdefault(arquivo, set()).add(pagina)
    return {arquivo: sorted(paginas) for arquivo, paginas in mapa.items()}


def mapa_das_paginas(numeros, paginas_por_arquivo, arquivo_preferido=None):
    """Monta o mapa quando o usuário pede páginas direto ("PDF da página 3").

    Parâmetros
    ----------
    numeros : list[int]
        Páginas pedidas. O valor -1 é um código especial que significa
        "a última página" (quem produz isso é `intencoes.pede_pagina`).
    paginas_por_arquivo : dict
        Vem de `recursos.paginas`, no formato {arquivo: {numero: texto}}.
        Usamos só para saber quais arquivos existem e quantas páginas têm.
    arquivo_preferido : str | None
        Quando a conversa já está falando de um arquivo específico, passamos
        o nome dele aqui para não exportar páginas de outros PDFs à toa.

    Devolve {arquivo: [páginas]}, já descartando páginas que não existem.
    """
    # Decide em quais arquivos vamos procurar as páginas pedidas.
    if arquivo_preferido and arquivo_preferido in paginas_por_arquivo:
        arquivos = [arquivo_preferido]
    else:
        arquivos = list(paginas_por_arquivo)

    mapa = {}
    for arquivo in arquivos:
        existentes = paginas_por_arquivo.get(arquivo, {})
        if not existentes:
            continue
        ultima = max(existentes)
        escolhidas = set()
        for numero in numeros:
            # -1 é o código de "última página": trocamos pelo número real.
            real = ultima if numero == -1 else numero
            if real in existentes:
                escolhidas.add(real)
        if escolhidas:
            mapa[arquivo] = sorted(escolhidas)
    return mapa


# ---------------------------------------------------------------------------
# PARTE 3 - Recortar de verdade as páginas do PDF original
# ---------------------------------------------------------------------------

def recortar_paginas(mapa, pasta_base="base"):
    """Copia as páginas pedidas dos PDFs originais para um PDF novo.

    Parâmetros
    ----------
    mapa : dict
        {arquivo: [páginas]} no formato humano (a primeira página é 1).
    pasta_base : str
        Pasta onde estão os PDFs originais.

    Retorna
    -------
    (bytes | None, list[str])
        Os bytes do PDF montado e a lista de rótulos do que entrou nele
        (ex.: ["FAQ.pdf - páginas 1, 5"]). Se nada pôde ser copiado,
        o primeiro item vem como None.
    """
    escritor = pypdf.PdfWriter()   # o PDF de saída, ainda vazio
    rotulos = []

    for arquivo, paginas in mapa.items():
        caminho = f"{pasta_base}/{arquivo}"
        try:
            leitor = pypdf.PdfReader(caminho)
        except Exception as erro:
            # Arquivo renomeado, movido ou corrompido: avisamos e seguimos.
            print(f"Não consegui abrir {caminho}: {erro}")
            continue

        copiadas = []
        for numero in paginas:
            indice = numero - 1          # humano (1) -> Python (0)
            if 0 <= indice < len(leitor.pages):
                escritor.add_page(leitor.pages[indice])
                copiadas.append(numero)

        if copiadas:
            plural = "páginas" if len(copiadas) > 1 else "página"
            rotulos.append(f"{arquivo} - {plural} {', '.join(map(str, copiadas))}")

    if not rotulos:
        return None, []

    # O PdfWriter escreve em qualquer objeto "tipo arquivo". Usamos um
    # BytesIO (um arquivo que vive só na memória) porque o Streamlit precisa
    # dos bytes para o botão de download, e não de um arquivo em disco.
    memoria = io.BytesIO()
    escritor.write(memoria)
    return memoria.getvalue(), rotulos


def nome_do_arquivo(mapa):
    """Nome amigável para o download: 'FAQ_paginas_1-5.pdf'."""
    if len(mapa) == 1:
        arquivo, paginas = next(iter(mapa.items()))
        base = re.sub(r"[^\w]+", "_", arquivo.rsplit(".", 1)[0]).strip("_")
        return f"{base}_paginas_{'-'.join(map(str, paginas))}.pdf"
    return "paginas_originais.pdf"


# ---------------------------------------------------------------------------
# PARTE 4 - Pedidos de download SEM a palavra "PDF"
# ---------------------------------------------------------------------------
#
# "quero o PDF da fonte" é fácil de detectar, porque tem a palavra PDF.
# Mas o usuário também escreve "quero baixar a fonte" ou "exporta a fonte".
# Nesses casos `pdf_utils.pediu_pdf()` devolve False (não há a palavra PDF),
# e sem esta função o pedido viraria uma pergunta comum para a IA.

# Verbos que mostram intenção de LEVAR O ARQUIVO (e não de ler na tela).
_ACOES_DE_DOWNLOAD = (
    r"baixa|baixar|baixe|download|exporta|exportar|exporte|salva|salvar|salve|"
    r"gera|gerar|gere|manda|mande|envia|enviar|passa|passe|anexa|anexar|arquivo"
)


def pedido_de_download_da_fonte(texto):
    """True para 'quero baixar a fonte', 'exporta a fonte', 'me manda o original'.

    Exige as DUAS coisas na frase:
      1) uma ação de download (baixar, exportar, salvar...)
      2) uma referência ao material original (fonte, base, original, página)

    Assim, 'quero ver a fonte' (só leitura) não entra aqui — esse caso mostra
    o texto na tela e o botão de download aparece junto, dentro de "Fontes".
    """
    t = texto.lower()
    if not pede_pdf_de_origem(t):
        return False
    if re.search(_ACOES_DE_DOWNLOAD, t):
        return True
    # "quero o documento original" também é pedido de arquivo, mas
    # "quero VER a fonte" é pedido de leitura: aí o texto aparece na tela
    # (com o botão de download junto, dentro de "Fontes").
    pede = re.search(r"\b(quero|queria|preciso|gostaria|me d[áa]|pode me dar)\b", t)
    leitura = re.search(r"\b(ver|vendo|mostrar?|mostre|exibir?|ler|leia|conte[úu]do|texto|"
                        r"abrir?|visualizar)\b", t)
    return bool(pede and not leitura)
