FROM python:3.12-slim

WORKDIR /app

COPY src/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app

EXPOSE 5050

ENTRYPOINT ["python", "main.py", "serve"]
