FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["gunicorn", "-c", "gunicorn.conf.py", "-w", "2", "app.main:app"]
