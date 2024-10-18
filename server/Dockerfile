 
FROM python:3.9-slim
 
ENV PYTHONUNBUFFERED=1
 
WORKDIR /app
 
COPY . /app
 
RUN pip install --no-cache-dir -r requirements.txt

 
EXPOSE 8000
 
CMD ["python3", "app/server.py"]
