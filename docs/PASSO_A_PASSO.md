> **Nota:** este arquivo é o registro da evolução do protótipo, versão por versão.
> Para instalação e visão geral do projeto, veja o [README](../README.md).
> O projeto não usa mais arquivo `.env` — toda a configuração fica em `rag_core.py`.

# RAG local com Ollama + Chroma: passo a passo

## O que cada arquivo faz
| Arquivo | Função |
|---|---|
| `base/` | Coloque aqui os PDFs que formam a base de conhecimento |
| `criar_db.py` | Lê os PDFs, divide em pedaços (chunks) e grava no banco vetorial `db/` |
| `embeddings.py` | Configura o modelo de embeddings (nomic-embed-text) com os prefixos recomendados |
| `main.py` | Faz as perguntas: busca os trechos relevantes e pede a resposta ao modelo |
| `backup_original/` | Cópia dos arquivos antes das melhorias |

## Como funciona (fluxo)
1. **Indexação (uma vez, ou sempre que mudar os PDFs):** PDFs → chunks de 800 caracteres → embeddings → Chroma.
2. **Pergunta:** a pergunta vira embedding → busca os 3 trechos mais parecidos.
3. **Filtro:** se o melhor trecho tiver score abaixo do limite, responde "fora do tema" sem chamar o modelo.
4. **Resposta:** os trechos + a pergunta vão ao modelo, que responde só com base neles.

## Passo 1: Preparar o Ollama
Com o Ollama instalado, baixe os modelos (uma vez):
```
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

## Passo 2: Instalar as dependências
```
pip install langchain langchain-community langchain-chroma langchain-ollama langchain-text-splitters pypdf python-dotenv
```

## Passo 3: Colocar os documentos
Copie os PDFs para a pasta `base/`.

## Passo 4: Criar o banco vetorial
```
python criar_db.py
```
Rode de novo sempre que adicionar, remover ou trocar PDFs, ou mudar `TAMANHO_CHUNK`.

## Passo 5: Fazer perguntas
```
python main.py
```
Digite as perguntas e `sair` para encerrar. O modelo carrega só uma vez, então da segunda pergunta em diante fica mais rápido.

## Passo 6: Calibrar o filtro "fora do tema"
O `main.py` mostra a linha `Scores: [...]` a cada pergunta.
1. Faça 5 perguntas que estão nos documentos e anote o primeiro score.
2. Faça 5 perguntas fora do tema e anote o primeiro score.
3. Ajuste `LIMITE_RELEVANCIA` para um valor entre os dois grupos.
4. Quando estiver satisfeito, coloque `MOSTRAR_SCORES = False`.

## Ajustes rápidos (topo do `main.py`)
| Quero... | Mude |
|---|---|
| Mais velocidade | Modelo menor em `MODELO_LLM`; `K_RESULTADOS = 2` |
| Respostas mais completas | `MODELO_LLM = "llama3"`; `K_RESULTADOS = 4` |
| Bloquear mais perguntas fora do tema | Aumentar `LIMITE_RELEVANCIA` |
| Parar de bloquear perguntas válidas | Diminuir `LIMITE_RELEVANCIA` |
| Trocar a mensagem de "fora do tema" | `MENSAGEM_FORA_DO_TEMA` |

## Problemas comuns
- **Lento mesmo assim:** rode `ollama ps` com o modelo carregado. Se mostrar `100% CPU`, use um modelo menor.
- **Erro de conexão:** o Ollama precisa estar aberto (`ollama serve`).
- **Mudei o chunk ou os PDFs e nada mudou:** rode `python criar_db.py` de novo.
- **Quer voltar ao original:** copie os arquivos de `backup_original/`.

---

# Chat visual (navegador) com memória e PDF sob demanda

## Arquivos novos
| Arquivo | Função |
|---|---|
| `app.py` | Tela de chat no navegador (Streamlit) |
| `rag_core.py` | Núcleo do RAG e **todas as configurações** (modelo, limite, k). Usado pelo chat e pelo terminal |
| `pdf_utils.py` | Gera o PDF e detecta quando o usuário pediu um PDF |
| `iniciar_chat.bat` | Dois cliques para abrir o chat (sem digitar comandos) |
| `requirements.txt` | Lista das bibliotecas |

> As configurações (`LIMITE_RELEVANCIA`, `MODELO_LLM` etc.) agora ficam em **`rag_core.py`**, e não mais no `main.py`.

## Passo 7: Instalar as novas bibliotecas
```
pip install streamlit fpdf2
```
(ou `pip install -r requirements.txt` para instalar tudo)

## Passo 8: Abrir o chat
- Dê dois cliques em **`iniciar_chat.bat`**, ou rode `python -m streamlit run app.py`.
- O navegador abre em `http://localhost:8501`.
- O Ollama precisa estar aberto.

## Como funciona
- **Memória:** as últimas 6 mensagens vão junto com cada pergunta. Se a pergunta for curta e parecer uma continuação ("e o segundo?"), o app a reescreve com base na conversa antes de buscar nos documentos.
- **Fora do tema:** continua passando pelo filtro de score. Perguntas fora do tema não entram na memória nem no PDF.
- **PDF só quando pedir:** escreva no chat, por exemplo:
  - `gera um PDF disso` → PDF da última resposta
  - `gera um PDF da conversa toda` → PDF com todas as respostas
  
  Aparece o botão **Baixar PDF** na própria mensagem. O PDF inclui as fontes (arquivo e página).
- **Nova conversa:** botão na barra lateral.

## Limitações
- Ao atualizar a página (F5), a conversa é apagada.
- Com um modelo de 3B, o reescrever de perguntas pode errar de vez em quando. Se uma pergunta fora do tema passar, aumente `LIMITE_RELEVANCIA` em `rag_core.py`.
- O PDF usa fonte padrão (sem emojis e sem alguns símbolos).

---

# Melhorias de fluidez (versão 3)

## O que mudou
| Problema | Solução |
|---|---|
| "Bom dia" respondia "Ai tem que abrir o pop" | Saudações e agradecimentos têm resposta própria e não passam pelo filtro |
| "Quais os tópicos do PDF?" não funcionava | O app lê os títulos numerados do próprio PDF e responde na hora, sem o modelo. Se o PDF não tiver títulos, o modelo resume trechos espalhados do documento |
| PDF gerado sem ninguém pedir | Só gera quando há um pedido real ("gera um PDF disso", "me manda em PDF"). Perguntas que só citam o PDF não geram nada |
| Modelo se recusava mesmo com o trecho certo | Prompt reescrito. Se ainda assim ele se recusar, o app mostra a mensagem padrão, sem fontes e fora do PDF |
| Texto do PDF extraído com uma palavra por linha | Novo leitor (`leitor_pdf.py`) que usa o modo layout e limpa o texto. Isso melhora a busca |

## Arquivos novos
`leitor_pdf.py` (leitura limpa), `topicos.py` (títulos e visão geral), `intencoes.py` (saudação, agradecimento, pedido de tópicos, recusa).

## Depois de atualizar
1. Feche a janela preta do chat e abra de novo o `iniciar_chat.bat`.
2. Rode `python criar_db.py` outra vez (o leitor e o tamanho dos chunks mudaram).
3. Se adicionar ou trocar PDFs, rode `criar_db.py` e reinicie o chat.

## Se as respostas ainda não ficarem naturais
O modelo de 3B é o limite. Se o computador aguentar, teste um maior em `rag_core.py`:
```
ollama pull qwen2.5:7b      (ou llama3.1:8b)
MODELO_LLM = "qwen2.5:7b"
```
Fica mais lento, mas segue instruções e escreve em português bem melhor.

---

# Como pedir o PDF (versão 4)

| Você escreve | O PDF contém |
|---|---|
| `gera um PDF sobre os projetos` | O assunto pedido: o app busca **esse assunto** nos documentos e gera o PDF com o conteúdo novo |
| `gera um PDF com os principais tópicos do documento` | A lista dos tópicos do PDF |
| `gera um PDF disso` / `da resposta anterior` | A última resposta |
| `gera um PDF da conversa toda` | Todas as respostas da conversa |

Se o assunto pedido não existir nos documentos, o app avisa e não gera o PDF.

---

# Ver o texto original (versão 5)

| Você escreve | O que aparece |
|---|---|
| `conteúdo da página 3` | O texto exato da página 3 do PDF (sem o modelo, na hora) |
| `conteúdo das páginas 2 a 4` | As páginas 2, 3 e 4 |
| `conteúdo da fonte` | O texto das páginas citadas na última resposta (até 3) |
| `gera um PDF da página 3` | PDF com o texto da página 3 |

Se a página não existir, o app informa quantas páginas o documento tem.

Formas aceitas para pedir páginas: `página 3`, `primeira página`, `segunda e terceira página`, `página dois`, `as duas primeiras páginas`, `páginas 2 a 4`, `última página`, `início do PDF`, `final do PDF`.

---

# Exportar as páginas originais da base (versão 6)

## Os dois tipos de PDF (a ideia central)

O app agora sabe entregar **dois PDFs diferentes**, e é importante entender a diferença:

| | PDF **gerado** | PDF **recortado** |
|---|---|---|
| Arquivo responsável | `pdf_utils.py` | `exportar_fontes.py` |
| Biblioteca | `fpdf` (desenha um PDF do zero) | `pypdf` (copia páginas prontas) |
| Conteúdo | O texto que a IA escreveu | As páginas originais da pasta `base`, intactas |
| Aparência | Formatação simples, sem emojis nem imagens | Igualzinha ao documento original |
| Quando usar | "gera um PDF dessa resposta" | "quero o PDF da fonte" |

O PDF recortado é a **prova original**: nada passou pela IA.

## Como pedir

| Você escreve | O que recebe |
|---|---|
| `quero o PDF da fonte` | As páginas originais citadas na última resposta |
| `exporta o PDF de onde você tirou isso` | O mesmo |
| `exporta o PDF da página 3` | A página 3 original |
| `gera um PDF da primeira e segunda página` | As páginas 1 e 2 originais |
| `quero o pdf da última página` | A última página original |
| `gera um PDF disso` | (continua sendo o PDF de **texto** da resposta) |

Se ainda não houver resposta na conversa e você não disser o número, o app avisa em vez de inventar.

## Como funciona por dentro (o que vale aprender)

A biblioteca `pypdf` tem dois objetos principais:

```python
leitor   = pypdf.PdfReader("base/arquivo.pdf")  # abre um PDF existente
escritor = pypdf.PdfWriter()                    # monta um PDF novo, vazio
escritor.add_page(leitor.pages[0])              # copia a página 1
escritor.add_page(leitor.pages[4])              # copia a página 5
```

**Cuidado com o índice:** para você a primeira página é a "1"; para o Python ela é `pages[0]`.
Por isso o código faz `indice = numero - 1`.

No fim, o PDF é escrito em um `io.BytesIO` — um arquivo que existe só na memória.
Fazemos assim porque o Streamlit precisa dos *bytes* para o botão de download,
e não de um arquivo salvo no disco.

### O caminho completo do pedido

```
Usuário: "quero o PDF da fonte"
   │
   ├─ pdf_utils.pediu_pdf()            → é um pedido de PDF?           (sim)
   ├─ exportar_fontes.pede_pdf_de_origem() → quer o ORIGINAL?          (sim)
   │
   ├─ a última resposta guardou:  fontes = ["FAQ.pdf (pág. 1)", "FAQ.pdf (pág. 5)"]
   ├─ mapa_das_fontes(fontes)          → {"FAQ.pdf": [1, 5]}
   ├─ recortar_paginas(mapa, "base")   → bytes do PDF + rótulo do que entrou
   │
   └─ st.download_button(...)          → o usuário baixa o arquivo
```

As funções de `exportar_fontes.py`, na ordem em que são usadas:

| Função | O que faz |
|---|---|
| `pede_pdf_de_origem(texto)` | Decide se o pedido é pelo material original |
| `mapa_das_fontes(fontes)` | `["FAQ.pdf (pág. 5)", "FAQ.pdf (pág. 1)"]` → `{"FAQ.pdf": [1, 5]}` |
| `mapa_das_paginas(numeros, ...)` | Monta o mapa quando o número veio na frase (trata `-1` = última) |
| `recortar_paginas(mapa, pasta)` | Copia as páginas e devolve os bytes do PDF |
| `nome_do_arquivo(mapa)` | Nome do download: `FAQ_paginas_1-5.pdf` |

O arquivo `exportar_fontes.py` está comentado linha a linha — vale abrir e ler junto com esta seção.

---

# Botão de download em toda resposta (versão 7)

## O problema que isso resolve
Antes, baixar o PDF original dependia de acertar a frase. Se você escrevesse
"quero baixar a fonte" (sem a palavra *PDF*), o app entendia como pergunta e
**escrevia um texto** em vez de entregar o arquivo.

## Agora
**Toda resposta** mostra, dentro de **Fontes**, o botão:

> ⬇️ Baixar estas páginas (PDF original)

Esse botão entrega as páginas originais da pasta `base`, recortadas do PDF de
origem. Não depende de frase nenhuma — é só abrir "Fontes" e clicar.

## Frases que também funcionam
| Você escreve | Resultado |
|---|---|
| `quero baixar a fonte` | Baixa as páginas originais |
| `exporta a fonte` / `salva a fonte` | Baixa as páginas originais |
| `quero o documento original` | Baixa as páginas originais |
| `quero o PDF da fonte` | Baixa as páginas originais |
| `quero **ver** a fonte` | Mostra o texto na tela **e** deixa o botão junto |

A regra é simples: verbo de **leitura** (ver, mostrar, ler) → texto na tela;
verbo de **arquivo** (baixar, exportar, salvar, gerar) → download.

## Detalhe de implementação (`app.py`)
A função `pdf_das_fontes(m)` recorta as páginas **uma única vez por mensagem** e
guarda os bytes dentro do próprio dicionário da mensagem (`m["pdf_fontes"]`).
Isso importa porque o Streamlit redesenha a tela inteira a cada clique — sem
esse cuidado, o PDF seria reaberto e recortado repetidas vezes.
