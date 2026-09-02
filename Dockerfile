FROM python:3.11-slim

# Pakai mirror Aliyun buat apt (biar cepat di jaringan China)
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Mirror pip Aliyun (ganti/hapus kalau jalan di luar China)
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/

COPY generate_readme.py app.py .

# /workspace/repo -> mount repo lokal di sini (read-only)
# /output          -> hasil README.md ditulis ke sini
RUN mkdir -p /workspace/repo /output

EXPOSE 8501

# Default: tampilkan help CLI. Override lewat docker-compose:
# - CLI: command: ["python", "generate_readme.py", "--repo", ...]
# - UI : command: ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
CMD ["python", "generate_readme.py", "--help"]
