FROM python:3.11-slim

WORKDIR /app
COPY report_server.py /app/report_server.py
RUN chmod +x /app/report_server.py

EXPOSE 8082

CMD ["python", "/app/report_server.py"]
