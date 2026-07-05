FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r web/requirements_web.txt

EXPOSE 8501

CMD ["streamlit", "run", "web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]