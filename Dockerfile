# Imagem oficial da Microsoft que JÁ VEM com Linux, Python 3.10+, e Chrome/Playwright instalados e configurados
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Váriaveis de ambiente Render
ENV PYTHONUNBUFFERED=1
ENV PORT=10000
# Render injeta PORT automaticamente — o valor acima é só fallback local

# Atualiza pip e instala os requisitos do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código principal
COPY . .

# Expor a porta gerada pelo Render
EXPOSE 5000

# Inicia o app usando gunicorn na porta fornecida pelo container
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 --worker-class gevent api:app
