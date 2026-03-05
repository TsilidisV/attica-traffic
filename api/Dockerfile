FROM python:3.12-slim

# 1. Install uv directly from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# --- HUGGING FACE SETUP: Create and switch to a non-root user (UID 1000) ---
RUN useradd -m -u 1000 user
USER user

# Set up the home directory and update the PATH for the virtual environment
ENV HOME=/home/user \
    PATH="/home/user/app/.venv/bin:$PATH"

# 2. Set the working directory to a folder inside the user's home directory
WORKDIR $HOME/app

# 3. Copy the workspace root files (Must use --chown to grant permissions to the new user)
COPY --chown=user pyproject.toml uv.lock ./
COPY --chown=user config.yaml ./api/

# 4. Copy the specific application folder
COPY --chown=user api ./api

# 5. Sync dependencies (uv will safely write caches to /home/user/.cache)
RUN uv sync --package attica-api --no-dev

# 6. Change the working directory to the API folder for runtime
WORKDIR $HOME/app/api

# 7. Expose the Hugging Face default port
EXPOSE 7860

# 8. Start Uvicorn bound to 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]