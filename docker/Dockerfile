# Use slim image for compatibility and smaller footprint
FROM python:3.11-slim

RUN apt-get update && apt-get install -y libfreetype6-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . .

ENTRYPOINT ["uv", "run", "pcb-render"]
