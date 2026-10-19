"""Versão de terminal (com memória da conversa). O chat visual é o app.py."""
import rag_core as rag


def main():
    recursos = rag.carregar_recursos()
    mensagens = []
    print("Pronto! Digite sua pergunta (ou 'sair' para encerrar).")
    while True:
        pergunta = input("\nEscreva sua pergunta: ").strip()
        if pergunta.lower() in ("sair", "exit", "q"):
            break
        if not pergunta:
            continue

        preparo = rag.preparar(recursos, pergunta, mensagens)
        if rag.MOSTRAR_SCORES and preparo.scores:
            print("Scores:", preparo.scores)
        if preparo.fora_do_tema:
            print(rag.MENSAGEM_FORA_DO_TEMA)
            continue

        print("\nResposta da IA: ", end="", flush=True)
        resposta = ""
        for pedaco in rag.gerar_stream(recursos, preparo.pergunta_busca, preparo, mensagens):
            resposta += pedaco
            print(pedaco, end="", flush=True)
        print()
        if preparo.modo != "conversa" and not rag.eh_recusa(resposta):
            mensagens.append({"role": "user", "content": pergunta, "tipo": "pergunta"})
            mensagens.append({"role": "assistant", "content": resposta, "tipo": "resposta"})


if __name__ == "__main__":
    main()
