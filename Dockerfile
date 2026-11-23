FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY . .
ENV PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN useradd -m monitor && chown -R monitor:monitor /srv
USER monitor
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
