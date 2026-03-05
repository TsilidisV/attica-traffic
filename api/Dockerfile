FROM python:3.12-slim

# 1. Install uv directly from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. Set the working directory to the root of the app
WORKDIR /app

# 3. Copy the workspace root files necessary for uv
COPY pyproject.toml uv.lock ./
COPY config.yaml ./api/

# 4. Copy the specific application folder
# Note: The path depends on where the build context is run from
COPY api ./api

# 5. Sync dependencies for the specific package
# Replace 'my-api' with the actual package name defined in apps/api/pyproject.toml
RUN uv sync --package attica-api --no-dev

# 6. Put the virtual environment on the PATH so we don't have to prefix commands with `uv run`
ENV PATH="/app/.venv/bin:$PATH"

# 7. Change the working directory to the API folder for runtime
WORKDIR /app/api

# 8. Expose the port your API runs on (assuming 8000 for standard ASGI servers)
EXPOSE 8000

# 9. Set the start command (adjust based on your framework, e.g., FastAPI/Uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]