# RAG Local (ANEEL)

Este script executa uma consulta RAG local com recuperação híbrida (lexical + vetorial) sobre documentos da ANEEL.

## O que o script faz

- recebe uma pergunta do usuário;
- recupera documentos com duas estratégias:
  - busca lexical BM25 no Elasticsearch;
  - busca vetorial no Chroma com embeddings Gemini;
- combina os recuperadores com `EnsembleRetriever`;
- monta um prompt com os trechos recuperados;
- gera resposta com modelo generativo Gemini;
- extrai as citações da resposta (ex.: `[1]`, `[2]`);
- agrega e anexa as fontes consultadas ao final da resposta.

## Arquitetura de recuperação

O pipeline usa 4 fases principais:

1. **Busca híbrida**: `ElasticsearchStore(BM25)` + `Chroma`.
2. **Augmentation**: construção de contexto textual com documentos recuperados.
3. **Generation**: chamada ao `ChatGoogleGenerativeAI`.
4. **Pós-processamento**: filtragem de citações e montagem das fontes finais.

Configuração do ensemble no script:

- `weights=[0.6, 0.4]` (prioridade lexical);
- `k=6` para recuperação lexical;
- `mmr` com `k=6` e `fetch_k=100` para recuperação vetorial.

## Requisitos

### 1) Variável de ambiente

Crie um `.env` na raiz do projeto com:

```env
GEMINI_API_KEY="sua_chave_aqui"
```

### 2) Serviços e dados

- Elasticsearch ativo em `http://localhost:9200`;
- índice lexical `aneel_lexical` já populado;
- base vetorial em `banco_chroma/` já gerada.

## Configurações padrão do script

- diretório Chroma: `banco_chroma`
- modelo de embeddings: `models/gemini-embedding-001`
- modelo generativo: `gemini-2.5-flash`
- URL Elasticsearch: `http://localhost:9200`
- índice Elasticsearch: `aneel_lexical`

## Execução

Na raiz do projeto:

```bash
python RAG/RAG.py
```

### Modo interativo

O script executa **modo interativo**, permitindo fazer múltiplas perguntas em sequência:

```
Digite sua pergunta para o Assistente da ANEEL: Qual é a potência instalada?
Resposta do Assistente:
...
```

Para sair do loop interativo, pressione **Ctrl+C** (ou Cmd+C no Mac).

O bloco `if __name__ == "__main__":` implementa um loop com tratamento de interrupção via teclado (`KeyboardInterrupt`).

## Função principal

```python
consultar_assistente_aneel(pergunta_usuario: str) -> tuple[str, list[Document]]
```

Retorno:

- `resposta_texto`: resposta final com seção de fontes (quando houver citações);
- `documentos_utilizados_final`: lista de `Document` efetivamente citados.

## Formato de citações e fontes

O prompt exige citação no formato `[n]` por frase com informação factual.

Após a geração, o script:

- identifica citações com regex;
- mapeia índices para documentos recuperados;
- agrupa por `id_processo`;
- adiciona ao final da resposta uma seção `**Fontes Consultadas:**` com:
  - índices citados;
  - ID do documento;
  - URL do documento.

## Observações

- Se o modelo não citar documentos, a seção de fontes não é anexada.
- A qualidade da resposta depende diretamente da indexação prévia em Chroma e Elasticsearch.
- O script suporta execução **interativa** via terminal, permitindo múltiplas consultas sem reinicializar.
- O script é uma versão local de teste e não expõe endpoint.