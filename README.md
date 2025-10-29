# 🧠 V2 LABS AI BETA 0.5

Suite de ferramentas para imagens (logo e ícones inline, API de remoção de fundo pronta para colar sua chave).

## Como executar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Conversor
- Resoluções: 1080x1080 ou 1080x1920
- Modos: Preencher com cor (JPG/PNG/WebP) ou Remover Fundo (API)
- Pré-visualizações e download ZIP
- **Cole sua API key** em `modules/conversor.py` na linha:
  `API_KEY = "YOUR_API_KEY_HERE"`

## Extrator CSV
- Baixa imagens de URLs listadas em CSV

## Deploy no Streamlit Cloud
- Suba tudo no GitHub como `v2-labs-ai-beta-0.5`
- Selecione `app.py` no Streamlit Cloud e faça o deploy
