"""Geração de PDF e detecção de pedido de PDF."""
import re
from datetime import datetime

from fpdf import FPDF

_GERAR = (
    r"gera|gerar|gere|cria|criar|crie|monta|montar|monte|exporta|exportar|salva|salvar|"
    r"baixa|baixar|manda|mande|envia|enviar|passa|passe|transforma|transformar|converte|converter"
)


def pediu_pdf(texto):
    """True só quando o usuário está PEDINDO um PDF (ex.: 'gera um PDF disso').
    Perguntas que apenas citam o PDF ('o que tem no PDF?') não contam."""
    t = texto.lower().strip()
    if not re.search(r"\bpdf\b", t):
        return False
    if len(re.findall(r"[a-zà-ÿ]+", t)) <= 3:                       # "pdf", "um pdf", "pdf por favor"
        return True
    for m in re.finditer(r"\b(" + _GERAR + r")\b[^.?!\n]{0,40}?\bpdf\b", t):
        if not re.search(r"\b(d[oa]|n[oa]|sobre|desse|deste)\s+pdf$", m.group(0)):
            return True
    if re.search(r"\b(em|como|num)\s+(um\s+)?pdf\b", t):             # "isso em PDF"
        return True
    return bool(re.search(
        r"\b(quero|queria|preciso|gostaria)( de)?( receber| baixar| ter)? (um |o )?pdf\b", t))


_REFERENCIAS = {
    "o", "a", "os", "as", "de", "do", "da", "dos", "das", "disso", "isso", "isto", "essa", "esse",
    "dessa", "desse", "resposta", "respostas", "anterior", "acima", "ultima", "última", "conversa",
    "tudo", "toda", "todo", "inteira", "completa", "completo", "mesmo", "mesma", "assunto",
    "conteudo", "conteúdo", "tema", "falamos", "falado", "conversamos", "agora", "tambem",
    "também", "ai", "aí", "ele", "ela", "em", "no", "na", "para", "pra", "com", "sobre", "que",
    "e", "ok", "pode", "poderia", "arquivo", "documento",
}


def extrair_assunto(texto):
    """Assunto pedido junto com o PDF, ou '' se o pedido só se refere ao que já foi dito.

    'gera um PDF sobre os projetos'  -> 'os projetos'   (conteúdo novo)
    'gera um PDF disso'              -> ''              (reaproveita a última resposta)
    """
    q = re.sub(
        r"\b(" + _GERAR + r")\b[^.?!\n]{0,40}?\bpdf\b"
        r"(\s+(sobre|com|d[oae]s?|acerca\s+d[oae]s?|que\s+(fala|explica|mostra)\s+(sobre|d[oae]s?)?)\b)?",
        " ", texto, flags=re.I)
    q = re.sub(
        r"\b(em|como|num)\s+(um\s+)?pdf\b|\bpdf\b|\bpor favor\b|\bpfv\b|"
        r"\b(quero|queria|preciso|gostaria)\b( de)?( receber| baixar| ter)?|\b(me|um|uma)\b",
        " ", q, flags=re.I)
    palavras = re.findall(r"[a-zà-ÿ0-9]+", q.lower())
    if not [p for p in palavras if p not in _REFERENCIAS]:
        return ""
    return re.sub(r"\s+", " ", q).strip(" ,.;:-?!")


def quer_conversa_toda(texto):
    return bool(
        re.search(r"\b(conversa|tudo|todas|todos|completo|completa|hist[óo]rico)\b", texto.lower())
    )


def _limpar(texto):
    """Remove markdown simples e troca caracteres que a fonte padrão não tem."""
    trocas = {"•": "-", "–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."}
    for a, b in trocas.items():
        texto = texto.replace(a, b)
    texto = texto.replace("**", "").replace("__", "").replace("`", "")
    return texto.encode("latin-1", "ignore").decode("latin-1")


def gerar_pdf(titulo, secoes, fontes=None):
    """secoes: lista de (subtitulo, texto). Retorna os bytes do PDF."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    largura = pdf.epw

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(largura, 9, _limpar(titulo), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(largura, 5, datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M"),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    for subtitulo, texto in secoes:
        if subtitulo:
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(largura, 7, _limpar(subtitulo), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        for linha in texto.splitlines():
            if linha.strip():
                pdf.multi_cell(largura, 6, _limpar(linha.rstrip()), new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.ln(3)
        pdf.ln(4)

    if fontes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(largura, 7, "Fontes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for f in fontes:
            pdf.multi_cell(largura, 5, _limpar("- " + f), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
