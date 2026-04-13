FROM python:3.11-slim

# Install uv
RUN pip install --no-cache-dir uv

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy pyproject.toml and lock file if exists
COPY pyproject.toml ./

# Sync dependencies
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy application code
COPY app/ /app/app/

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
