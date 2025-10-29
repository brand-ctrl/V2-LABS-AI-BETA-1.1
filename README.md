# V2 LABS AI BETA 1.0

- Conversor de Imagens (apenas cor sólida)
- Removedor de Fundo (Python puro via rembg) → gera PNG com transparência
- Extrator de Imagens CSV
- Fundo azul #e9f5ff com degradê, logo no topo + favicon

## Rodar
pip install -r requirements.txt
streamlit run app.py

## Observações
- rembg usa onnxruntime; a primeira execução pode baixar o modelo.
