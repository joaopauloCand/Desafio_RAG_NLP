# Testador RAG - Juiz Pontuador

Este script avalia automaticamente a qualidade das respostas do seu RAG usando um LLM como juiz técnico.

## O que o script faz

- carrega um dataset de perguntas e gabaritos esperados;
- executa o RAG para cada pergunta (`consultar_assistente_aneel`);
- envia a pergunta, o gabarito, o contexto recuperado e a resposta do RAG para um juiz LLM;
- recebe notas de 1 a 5 em três métricas de qualidade;
- salva um relatório final em CSV;
- imprime médias consolidadas no final da execução.

## Métricas avaliadas

O juiz retorna nota e justificativa para:

- `fidelidade`: se a resposta alucina ou se mantém fiel ao contexto;
- `relevancia_resposta`: se a resposta atende à pergunta e ao gabarito;
- `relevancia_contexto`: se os documentos recuperados eram úteis para responder.

## Entrada esperada

Arquivo JSON com uma lista de objetos contendo, no mínimo:

- `pergunta`
- `resposta_esperada`

Campo opcional:

- `tipo`

Exemplo:

```json
[
  {
    "pergunta": "Resuma o despacho X?",
    "resposta_esperada": "O despacho X...",
    "tipo": "Resumo"
  }
]
```

## Saída gerada

O script gera um CSV com colunas como:

- `Pergunta`
- `Tipo`
- `Gabarito`
- `Resposta_do_RAG`
- `Nota_Fidelidade`, `Just_Fidelidade`
- `Nota_Rel_Resposta`, `Just_Rel_Resposta`
- `Nota_Rel_Contexto`, `Just_Rel_Contexto`

Por padrão:

- entrada: `testador_rag/perguntas_teste_rag.json`
- saída: `testador_rag/teste_resultado.csv`

## Pré-requisitos

- variável `GEMINI_API_KEY` configurada no `.env` da raiz;
- base vetorial e índice lexical já preparados para o RAG;
- dependências da etapa instaladas (arquivo dedicado abaixo).

Para evitar instalar pacotes desnecessários para quem só usa etapas posteriores do pipeline, esta pasta possui um arquivo dedicado:

- `testador_rag/requirements.txt`

Instale apenas se quiser executar/refazer esta etapa:

```bash
pip install -r testador_rag/requirements.txt
```

## Execução

Na raiz do projeto, execute:

```bash
python testador_rag/juiz_pontuador.py
```

## Robustez e comportamento

- tenta até 3 vezes por item em caso de erro;
- aplica espera adicional para erros de limite de cota (`429`/`RESOURCE_EXHAUSTED`);
- permite interrupção com `Ctrl+C`, mantendo os resultados já acumulados;
- só grava CSV se houver ao menos um resultado processado.

## Observações

- O script depende do módulo `RAG/RAG.py` e da função `consultar_assistente_aneel`.
- As notas refletem julgamento automatizado do LLM e devem ser usadas como apoio, não como verdade absoluta.