# ---- builder ---- (Python 3.11 to match the distroless runtime's interpreter)
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
# Install into a self-contained dir we can copy wholesale into the runtime stage
RUN pip install --target=/packages -r requirements.txt

# ---- runtime ----
# distroless: no shell, no package manager — minimal attack surface.
# :nonroot already runs as uid 65532, so no useradd step is needed.
FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app

ENV PYTHONPATH=/packages \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Installed via `pip install --target`, so Streamlit can't detect a normal
    # site-packages install and would default to development mode (which rejects
    # --server.port). Force it off.
    STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

COPY --from=builder /packages /packages
COPY . .

EXPOSE 8501

# The base image's ENTRYPOINT is python3, so streamlit is invoked as a module.
CMD ["-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
