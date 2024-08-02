FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "uvicorn[standard]"

COPY main.py .

EXPOSE 8080

CMD ["uvicorn", "main.app:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "300"]