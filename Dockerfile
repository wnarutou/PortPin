FROM python:3.12-slim

WORKDIR /app

COPY portpin.py .
COPY config.json .

ENTRYPOINT ["python", "portpin.py"]
CMD ["--config", "/app/config.json"]
