FROM python:3.12-slim
RUN useradd --create-home --uid 10001 helpdesk && mkdir /dados && chown helpdesk /dados
WORKDIR /codigo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
USER helpdesk
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_URL=sqlite:////dados/inventario.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
