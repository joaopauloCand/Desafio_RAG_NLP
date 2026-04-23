import json

def auditar_jsonl(caminho_arquivo: str) -> int:
    """Audita a integridade do arquivo JSONL, contando quantos chunks estão perfeitamente formatados e alertando sobre quaisquer linhas corrompidas."""
    total_linhas = 0
    linhas_corrompidas = 0

    print(f"Iniciando auditoria de integridade: {caminho_arquivo}...")
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        for num_linha, linha in enumerate(f, 1):
            try:
                # Tenta converter a string de volta para dicionário
                # Se isso funcionar, sabemos que o dado está 100% íntegro
                dados = json.loads(linha)
                total_linhas += 1
                
            except json.JSONDecodeError:
                print(f"⚠️ Erro de formatação JSON na linha {num_linha}")
                linhas_corrompidas += 1

    print("-" * 30)
    print("Auditoria Concluída!")
    print(f"✅ Chunks perfeitamente saudáveis: {total_linhas}")
    
    if linhas_corrompidas > 0:
        print(f"❌ Atenção: {linhas_corrompidas} blocos estão corrompidos.")
    else:
        print("✅ Status: 100% Seguro. Pronto para a fase de Embeddings!")
        
    return total_linhas

def main():
    caminho_arquivo = "chunking\\chunks\\chunks_markdown.jsonl" # <-- Altere para o caminho do seu arquivo JSONL
    auditar_jsonl(caminho_arquivo)

#Rode esse script para verificar a integridade dos seus chunks antes de avançar para a fase de embeddings. 
# Ele irá contar quantos chunks estão perfeitamente formatados e alertar sobre quaisquer linhas corrompidas.
if __name__ == "__main__":
    main()