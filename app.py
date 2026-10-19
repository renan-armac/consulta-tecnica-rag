import streamlit as st

import rag_core as rag
from exportar_fontes import (mapa_das_fontes, mapa_das_paginas, nome_do_arquivo,
                              pede_pdf_de_origem, pedido_de_download_da_fonte,
                              recortar_paginas)
from intencoes import pede_pagina
from pdf_utils import extrair_assunto, gerar_pdf, pediu_pdf, quer_conversa_toda

st.set_page_config(page_title="Assistente RAG", page_icon="💬", layout="centered")


@st.cache_resource(show_spinner="Carregando modelos...")
def carregar():
    return rag.carregar_recursos()


recursos = carregar()

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
mensagens = st.session_state.mensagens

# ---------------------------- Barra lateral ----------------------------
with st.sidebar:
    st.header("Assistente RAG")
    if st.button("Nova conversa", use_container_width=True):
        st.session_state.mensagens = []
        st.rerun()
    st.caption(
        "Pergunte sobre os documentos. Para receber um PDF, peça no chat:\n\n"
        "- **gera um PDF sobre os projetos** → PDF com o assunto pedido\n"
        "- **gera um PDF disso** → PDF da última resposta\n"
        "- **gera um PDF da conversa toda** → PDF com todas as respostas\n"
        "- **quero baixar a fonte** → as páginas originais da base, recortadas do PDF\n\n"
        "Toda resposta traz, em **Fontes**, o botão para baixar as páginas originais."
    )
    with st.expander("Configurações em uso"):
        st.write(f"Modelo: `{rag.MODELO_LLM}`")
        st.write(f"Limite de relevância: `{rag.LIMITE_RELEVANCIA}`")
        st.write(f"Trechos por pergunta: `{rag.K_RESULTADOS}`")

st.title("💬 Assistente RAG")


def pdf_das_fontes(m):
    """Recorta as páginas originais citadas na mensagem e guarda o resultado.

    O recorte é feito uma única vez por mensagem: na primeira exibição
    guardamos os bytes dentro do próprio dicionário da mensagem, para não
    reabrir o PDF a cada vez que o Streamlit redesenha a tela."""
    if "pdf_fontes" not in m:
        mapa = mapa_das_fontes(m.get("fontes"))
        dados, _ = recortar_paginas(mapa, rag.PASTA_BASE) if mapa else (None, [])
        m["pdf_fontes"] = dados
        m["pdf_fontes_nome"] = nome_do_arquivo(mapa) if mapa else ""
    return m["pdf_fontes"]


def mostrar_extras(m, chave):
    if m.get("fontes"):
        with st.expander("Fontes"):
            for f in m["fontes"]:
                st.write("- " + f)
            # Botão sempre disponível: baixa as páginas ORIGINAIS da base,
            # recortadas do PDF de origem (sem passar pela IA).
            original = pdf_das_fontes(m)
            if original:
                st.download_button(
                    "⬇️ Baixar estas páginas (PDF original)", data=original,
                    file_name=m["pdf_fontes_nome"], mime="application/pdf",
                    key=f"fonte_{chave}",
                )
    if m.get("pdf"):
        st.download_button(
            "Baixar PDF", data=m["pdf"], file_name=m["pdf_nome"],
            mime="application/pdf", key=f"dl_{chave}",
        )


def responder(pergunta, historico, quer_pdf=False):
    """Mostra a resposta no balão do assistente e devolve a mensagem a guardar.
    Com quer_pdf=True, o PDF é gerado com o conteúdo desta resposta."""
    with st.spinner("Buscando nos documentos..."):
        preparo = rag.preparar(recursos, pergunta, historico)

    aviso = "\n\n*Não encontrei isso nos documentos, então não gerei o PDF.*" if quer_pdf else ""

    if preparo.fora_do_tema:
        texto = rag.MENSAGEM_FORA_DO_TEMA + aviso
        st.markdown(texto)
        if rag.MOSTRAR_SCORES:
            st.caption(f"Scores: {preparo.scores}")
        return {"role": "assistant", "content": texto, "tipo": "fora_do_tema"}

    espaco = st.empty()
    with espaco.container():
        resposta = st.write_stream(
            rag.gerar_stream(recursos, preparo.pergunta_busca, preparo, historico)
        )

    if preparo.modo == "conversa":  # saudação / agradecimento: fora da memória e do PDF
        return {"role": "assistant", "content": resposta, "tipo": "conversa"}

    if rag.eh_recusa(resposta):  # o modelo se recusou: mensagem padrão, sem fontes
        texto = rag.MENSAGEM_FORA_DO_TEMA + aviso
        espaco.markdown(texto)
        return {"role": "assistant", "content": texto, "tipo": "fora_do_tema"}

    titulo = preparo.titulo or ("Principais tópicos do documento"
                                if preparo.modo == "visao_geral" else pergunta[:120])
    msg = {
        "role": "assistant", "content": resposta, "tipo": "resposta",
        "pergunta": titulo,
        "fontes": preparo.fontes or rag.listar_fontes(preparo.resultados),
    }
    if quer_pdf:
        msg["pdf"] = gerar_pdf(titulo, [("", resposta)], msg["fontes"])
        msg["pdf_nome"] = "resposta.pdf"
    mostrar_extras(msg, len(mensagens))
    if rag.MOSTRAR_SCORES and preparo.scores:
        st.caption(f"Scores: {preparo.scores}")
    return msg


# Reexibe a conversa a cada interação
for i, m in enumerate(mensagens):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        mostrar_extras(m, i)

entrada = st.chat_input("Escreva sua pergunta...")

if entrada:
    with st.chat_message("user"):
        st.markdown(entrada)
    historico_antes = list(mensagens)  # memória: tudo que veio antes desta mensagem

    pdf_pedido = pediu_pdf(entrada)
    assunto = ""
    if pdf_pedido and not quer_conversa_toda(entrada):
        assunto = extrair_assunto(entrada)  # '' = "disso", "da resposta anterior"...

    # Páginas pedidas direto no texto ("PDF da página 3", "PDF da primeira página").
    paginas_pedidas = pede_pagina(entrada) if pdf_pedido else []
    # O usuário quer o material ORIGINAL (a fonte), e não um texto escrito pela IA?
    quer_original = (pdf_pedido and (paginas_pedidas or pede_pdf_de_origem(entrada))
                     # "quero baixar a fonte" / "exporta a fonte" (sem a palavra PDF)
                     or pedido_de_download_da_fonte(entrada))

    # ---- PDF com as PÁGINAS ORIGINAIS da base (recortadas do PDF de origem) ----
    if quer_original:
        mensagens.append({"role": "user", "content": entrada, "tipo": "pedido_pdf"})

        # De onde vêm as páginas? Duas situações:
        #   a) o usuário disse o número  -> usamos o que ele pediu
        #   b) ele disse "da fonte"      -> usamos as fontes da última resposta
        #
        # Nem toda resposta cita página: a lista de tópicos, por exemplo, cita
        # só o nome do arquivo. Por isso procuramos de trás para frente a
        # última resposta que realmente tenha "(pág. N)" nas fontes.
        fontes_anteriores = []
        for m in reversed(mensagens):
            if m.get("tipo") == "resposta" and mapa_das_fontes(m.get("fontes")):
                fontes_anteriores = m["fontes"]
                break

        if paginas_pedidas:
            # Se a conversa já cita um arquivo, damos preferência a ele.
            preferido = next(iter(mapa_das_fontes(fontes_anteriores)), None)
            mapa = mapa_das_paginas(paginas_pedidas, recursos.paginas, preferido)
        else:
            mapa = mapa_das_fontes(fontes_anteriores)

        with st.chat_message("assistant"):
            if not mapa:
                texto = ("Não sei quais páginas exportar. Faça uma pergunta primeiro "
                         "(aí eu uso as fontes da resposta) ou diga o número, "
                         "por exemplo: *exporta o PDF da página 3*.")
                st.markdown(texto)
                mensagens.append({"role": "assistant", "content": texto, "tipo": "aviso"})
            else:
                arquivo_pdf, rotulos = recortar_paginas(mapa, rag.PASTA_BASE)
                if not arquivo_pdf:
                    texto = "Não consegui abrir o PDF original na pasta `base` para recortar as páginas."
                    st.markdown(texto)
                    mensagens.append({"role": "assistant", "content": texto, "tipo": "aviso"})
                else:
                    msg = {
                        "role": "assistant", "tipo": "pdf",
                        "pdf": arquivo_pdf, "pdf_nome": nome_do_arquivo(mapa),
                        "content": "Pronto! Recortei do documento original: " + "; ".join(rotulos) + ".",
                        "fontes": [f"{a} (pág. {p})" for a, ps in mapa.items() for p in ps],
                    }
                    st.markdown(msg["content"])
                    mostrar_extras(msg, len(mensagens))
                    mensagens.append(msg)

    # ---- PDF de um assunto novo: busca o assunto nos documentos e gera o PDF com ele ----
    elif pdf_pedido and assunto:
        mensagens.append({"role": "user", "content": entrada, "tipo": "pergunta"})
        with st.chat_message("assistant"):
            msg = responder(assunto, historico_antes, quer_pdf=True)
        if msg["tipo"] in ("fora_do_tema", "conversa"):
            mensagens[-1]["tipo"] = msg["tipo"]
        mensagens.append(msg)

    # ---- PDF do que já foi dito (última resposta ou conversa toda) ----
    elif pdf_pedido:
        mensagens.append({"role": "user", "content": entrada, "tipo": "pedido_pdf"})
        respostas = [m for m in mensagens if m.get("tipo") == "resposta"]
        with st.chat_message("assistant"):
            if not respostas:
                texto = "Ainda não há nenhuma resposta nesta conversa para virar PDF. Faça uma pergunta primeiro."
                st.markdown(texto)
                mensagens.append({"role": "assistant", "content": texto, "tipo": "aviso"})
            else:
                if quer_conversa_toda(entrada):
                    titulo = "Resumo da conversa"
                    secoes = [(m["pergunta"], m["content"]) for m in respostas]
                    fontes = sorted({f for m in respostas for f in m.get("fontes", [])})
                else:
                    ultima = respostas[-1]
                    titulo = ultima["pergunta"]
                    secoes = [("", ultima["content"])]
                    fontes = ultima.get("fontes", [])
                msg = {
                    "role": "assistant", "tipo": "pdf",
                    "pdf": gerar_pdf(titulo, secoes, fontes), "pdf_nome": "resposta.pdf",
                    "content": "Pronto! Gerei o PDF com o que conversamos.",
                }
                st.markdown(msg["content"])
                mostrar_extras(msg, len(mensagens))
                mensagens.append(msg)

    # ---------------- Pergunta normal ----------------
    else:
        mensagens.append({"role": "user", "content": entrada, "tipo": "pergunta"})
        with st.chat_message("assistant"):
            msg = responder(entrada, historico_antes)
        if msg["tipo"] in ("fora_do_tema", "conversa"):
            mensagens[-1]["tipo"] = msg["tipo"]  # não entra na memória nem no PDF
        mensagens.append(msg)
