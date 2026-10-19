"""Gera o PDF de exemplo usado na pasta `base/`.

O conteúdo é FICTÍCIO, escrito para este repositório. Serve para que quem
clonar o projeto consiga rodar e testar sem precisar de nenhum documento real.

A estrutura imita um FAQ corporativo: títulos numerados em MAIÚSCULAS
("1. COMO SOLICITAR..."), que é o padrão reconhecido por `topicos.py`
para montar a lista de assuntos do documento.

Uso:  python docs/gerar_pdf_exemplo.py
"""
from fpdf import FPDF

TITULO = "Manual de Operacao - Minicarregadeira MC-250 (documento ficticio)"

SECOES = [
    ("COMO SOLICITAR A LOCACAO DO EQUIPAMENTO",
     "A solicitacao e feita pelo portal do cliente ou pela central de atendimento. "
     "E necessario informar o periodo desejado, o endereco da obra e o responsavel "
     "pelo recebimento. O prazo medio de confirmacao e de 2 dias uteis. "
     "Para obras fora da regiao metropolitana, considere 5 dias uteis."),
    ("QUAL O VALOR DA DIARIA E DA LOCACAO MENSAL",
     "A diaria da Minicarregadeira MC-250 e de R$ 480,00, com franquia de 8 horas "
     "de uso por dia. A locacao mensal custa R$ 7.900,00, com franquia de 176 horas. "
     "Horas excedentes sao cobradas a R$ 65,00 por hora. O valor nao inclui "
     "combustivel nem o transporte ate a obra."),
    ("O QUE ESTA INCLUIDO NA MANUTENCAO PREVENTIVA",
     "A manutencao preventiva e responsabilidade da locadora e inclui troca de oleo "
     "e filtros a cada 250 horas, inspecao do sistema hidraulico, verificacao dos "
     "pneus e revisao do sistema eletrico. O cliente deve apenas registrar o "
     "horimetro semanalmente e informar qualquer ruido ou vazamento."),
    ("QUAL A CAPACIDADE E AS DIMENSOES DA MC-250",
     "A capacidade operacional nominal e de 950 kg. O peso operacional do "
     "equipamento e de 3.200 kg. A altura maxima de despejo e de 2,45 metros. "
     "A largura total e de 1,68 metro, o que permite a passagem em corredores "
     "estreitos de obra. O motor e diesel, de 74 HP."),
    ("QUAIS SAO OS REQUISITOS DE SEGURANCA PARA O OPERADOR",
     "O operador deve possuir treinamento NR-11 valido e utilizar capacete, botina "
     "com biqueira de aco, protetor auricular e colete refletivo. E obrigatorio o "
     "uso do cinto de seguranca da cabine. A operacao em rampas acima de 15 graus "
     "exige autorizacao previa do engenheiro responsavel pela obra."),
    ("COMO PROCEDER EM CASO DE PANE OU ACIDENTE",
     "Desligue o equipamento, acione o freio de estacionamento e isole a area. "
     "Comunique a central de emergencia em ate 1 hora. Nao tente reparar o "
     "equipamento por conta propria: isso cancela a cobertura do seguro. "
     "O atendimento tecnico em campo ocorre em ate 24 horas uteis."),
    ("QUAL O PROCEDIMENTO PARA DEVOLUCAO DO EQUIPAMENTO",
     "A devolucao deve ser agendada com 3 dias uteis de antecedencia. O equipamento "
     "precisa estar limpo e com o tanque de combustivel no mesmo nivel da entrega. "
     "E feita uma vistoria conjunta, com registro fotografico. Avarias identificadas "
     "na vistoria sao orcadas e cobradas em fatura separada."),
    ("COMO E CALCULADA A MULTA POR ATRASO NA DEVOLUCAO",
     "O atraso na devolucao gera cobranca de diaria cheia por dia corrido, acrescida "
     "de multa de 20% sobre o valor da diaria. Atrasos superiores a 5 dias sem "
     "comunicacao previa podem gerar acionamento juridico, conforme a clausula 8 "
     "do contrato de locacao."),
]


def gerar(caminho="base/manual-exemplo.pdf"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    largura = pdf.epw

    pdf.set_font("Helvetica", "B", 15)
    pdf.multi_cell(largura, 8, TITULO, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(largura, 5,
                   "Documento de exemplo, com dados ficticios, criado apenas para "
                   "demonstrar o funcionamento deste projeto.",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    for numero, (titulo, corpo) in enumerate(SECOES, 1):
        # Quebra de pagina a cada 3 secoes: assim o PDF tem varias paginas e
        # da para demonstrar a citacao de fontes ("pag. 2") e a exportacao
        # das paginas originais.
        if numero > 1 and numero % 3 == 1:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(largura, 6, f"{numero}. {titulo}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(largura, 6, corpo, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    pdf.output(caminho)
    print(f"PDF de exemplo criado em: {caminho}")


if __name__ == "__main__":
    gerar()
