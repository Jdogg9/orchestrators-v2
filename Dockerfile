FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY gunicorn.conf.py ./gunicorn.conf.py

EXPOSE 8088

ENV ORCH_HOST=0.0.0.0
ENV ORCH_PORT=8088

CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.server:app"]
