# Última versão de Python e de Alpine
FROM python:3.10-slim

# Configura diretório principal
WORKDIR /app

# Copia arquivo para diretório principal
COPY requirements.txt .

# Instala última versão do pip e bibliotecas requeridas
# No cache: Execução determinística & imagem menor
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
# Adicionado após 'RUN pip' para otimização de layer caching
# (Mantém cache de instalação se houver mudança de código)
COPY . .

# Declara a qual porta do contêiner a aplicação escutará
# (Utilizado por Docker Compose)
EXPOSE 8000 

# Executa servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]