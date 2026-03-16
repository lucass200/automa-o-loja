# Usa a imagem oficial do Python slim
FROM python:3.12-slim

# Define a pasta de trabalho
WORKDIR /app

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Atualiza sistema e instala dependências necessárias para o Chrome e Playwright rodarem
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de requerimentos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o navegador do Playwright (Chromium) no Linux da nuvem
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# Copia todo o código da automação para o container
COPY . .

# Expõe a porta que o servidor vai usar
EXPOSE 5000

# Comando para iniciar: Gunicorn chamando a aplicação Flask no api.py
CMD gunicorn --bind 0.0.0.0:$PORT api:app
