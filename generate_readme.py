#!/usr/bin/env python3
"""
README Generator - LangGraph + DashScope (qwen3.6-plus)
Generate README.md otomatis dari repo lokal atau repo git eksternal.

Contoh pakai (di dalam container):
  python generate_readme.py --repo /workspace/repo --output /output/README.md
  python generate_readme.py --repo-url https://github.com/user/proyek.git --output /output/README.md
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import git

load_dotenv()

DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus")

# File/dir yang di-skip saat scan tree (biar konteks nggak kebanjiran)
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".next", "target", ".idea", ".vscode", ".pytest_cache",
    "coverage", ".mypy_cache",
}
IGNORE_EXT = {".pyc", ".lock", ".log", ".png", ".jpg", ".jpeg", ".gif",
              ".ico", ".woff", ".woff2", ".ttf", ".eot", ".zip", ".tar",
              ".gz", ".pdf", ".mp4", ".mp3"}

# File kunci yang kalau ada, isinya ikut dibaca (bukan cuma nama)
KEY_FILES = [
    "package.json", "pyproject.toml", "requirements.txt", "setup.py",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
    "main.py", "app.py", "index.js", "index.ts", "main.go",
]

MAX_TREE_LINES = 200
MAX_FILE_CHARS = 3000
MAX_TOTAL_CONTEXT_CHARS = 20000


class RepoState(TypedDict):
    repo_path: str
    output_path: str
    language: str
    file_tree: str
    key_contents: str
    existing_readme: Optional[str]
    draft: str
    final_readme: str


def build_authenticated_url(repo_url: str, username: str = None, password: str = None) -> str:
    """Sisipkan username:password/token ke URL git (buat repo private, mis. GitLab CE self-hosted)."""
    if not username and not password:
        return repo_url
    from urllib.parse import urlsplit, urlunsplit, quote
    parts = urlsplit(repo_url)
    user = quote(username or "", safe="")
    pw = quote(password or "", safe="")
    netloc = f"{user}:{pw}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def clone_repo(repo_url: str, dest: str, username: str = None, password: str = None) -> str:
    auth_url = build_authenticated_url(repo_url, username, password)
    print(f"[+] Cloning {repo_url} ...")
    git.Repo.clone_from(auth_url, dest, depth=1)
    return dest


def build_file_tree(root: str) -> str:
    lines = []
    root_path = Path(root)
    for path in sorted(root_path.rglob("*")):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in IGNORE_EXT:
            continue
        rel = path.relative_to(root_path)
        depth = len(rel.parts) - 1
        prefix = "  " * depth
        marker = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{marker}")
        if len(lines) >= MAX_TREE_LINES:
            lines.append("... (truncated)")
            break
    return "\n".join(lines)


def read_key_files(root: str) -> str:
    root_path = Path(root)
    chunks = []
    total = 0
    for name in KEY_FILES:
        for match in root_path.rglob(name):
            if any(part in IGNORE_DIRS for part in match.parts):
                continue
            try:
                content = match.read_text(errors="ignore")[:MAX_FILE_CHARS]
            except Exception:
                continue
            rel = match.relative_to(root_path)
            chunk = f"\n--- {rel} ---\n{content}\n"
            if total + len(chunk) > MAX_TOTAL_CONTEXT_CHARS:
                break
            chunks.append(chunk)
            total += len(chunk)
    return "".join(chunks)


def find_existing_readme(root: str) -> Optional[str]:
    for name in ["README.md", "readme.md", "Readme.md"]:
        p = Path(root) / name
        if p.exists():
            return p.read_text(errors="ignore")[:MAX_FILE_CHARS]
    return None


def get_llm() -> ChatOpenAI:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        sys.exit("[!] ENV DASHSCOPE_API_KEY belum di-set.")
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url=DASHSCOPE_BASE_URL,
        api_key=api_key,
        temperature=0.3,
    )


# ---------- LangGraph nodes ----------

def node_scan(state: RepoState) -> RepoState:
    print("[+] Scanning struktur repo...")
    state["file_tree"] = build_file_tree(state["repo_path"])
    state["key_contents"] = read_key_files(state["repo_path"])
    state["existing_readme"] = find_existing_readme(state["repo_path"])
    return state


SYSTEM_PROMPTS = {
    "id": (
        "Kamu adalah generator README.md profesional untuk proyek software. "
        "Buat README yang jelas, terstruktur, dan sesuai isi repo yang diberikan. "
        "Sertakan section: judul, deskripsi singkat, fitur utama, tech stack, "
        "cara instalasi, cara menjalankan/penggunaan, struktur folder (ringkas), "
        "dan lisensi (jika ada indikasi). Jangan mengarang fitur yang tidak "
        "terlihat dari kode. Tulis seluruh README dalam Bahasa Indonesia. "
        "Output HANYA markdown README, tanpa komentar tambahan."
    ),
    "en": (
        "You are a professional README.md generator for software projects. "
        "Write a clear, well-structured README based on the given repo content. "
        "Include sections: title, short description, key features, tech stack, "
        "installation, usage/running instructions, folder structure (brief), "
        "and license (if there's an indication). Do not invent features that "
        "aren't visible in the code. Write the entire README in English. "
        "Output ONLY the README markdown, no extra commentary."
    ),
}


def node_draft(state: RepoState) -> RepoState:
    print(f"[+] Generating draft README (lang={state['language']}) via DashScope...")
    llm = get_llm()

    lang = state.get("language", "id")
    system = SystemMessage(content=SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["id"]))

    existing = state.get("existing_readme") or "(tidak ada README sebelumnya)"

    human = HumanMessage(content=f"""
Struktur folder repo:
{state['file_tree']}

Isi file kunci (config/manifest/entrypoint):
{state['key_contents']}

README lama (kalau ada, jadikan referensi konteks, jangan disalin mentah):
{existing}
""")

    response = llm.invoke([system, human])
    state["draft"] = response.content
    return state


def node_finalize(state: RepoState) -> RepoState:
    state["final_readme"] = state["draft"].strip() + "\n"
    return state


def build_graph():
    graph = StateGraph(RepoState)
    graph.add_node("scan", node_scan)
    graph.add_node("generate_draft", node_draft)
    graph.add_node("finalize", node_finalize)
    graph.set_entry_point("scan")
    graph.add_edge("scan", "generate_draft")
    graph.add_edge("generate_draft", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_pipeline(repo_path: str, language: str = "id") -> str:
    """Reusable entrypoint (dipakai CLI dan Streamlit UI)."""
    graph = build_graph()
    result = graph.invoke({
        "repo_path": repo_path,
        "output_path": "",
        "language": language,
        "file_tree": "",
        "key_contents": "",
        "existing_readme": None,
        "draft": "",
        "final_readme": "",
    })
    return result["final_readme"]


def main():
    parser = argparse.ArgumentParser(description="Generate README.md otomatis dari repo (LangGraph + DashScope)")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo", help="Path lokal ke repo (misal /workspace/repo)")
    src.add_argument("--repo-url", help="URL git repo eksternal (akan di-clone)")
    parser.add_argument("--output", default="/output/README.md", help="Path output README.md")
    parser.add_argument("--lang", choices=["id", "en"], default=os.getenv("README_LANG", "id"), help="Bahasa output README (atau ENV README_LANG)")
    parser.add_argument("--git-username", default=os.getenv("GIT_USERNAME"), help="Username untuk repo private (atau ENV GIT_USERNAME)")
    parser.add_argument("--git-password", default=os.getenv("GIT_TOKEN"), help="Password/token untuk repo private (atau ENV GIT_TOKEN)")
    args = parser.parse_args()

    tmp_dir = None
    try:
        if args.repo_url:
            tmp_dir = tempfile.mkdtemp(prefix="readme-src-")
            repo_path = clone_repo(args.repo_url, tmp_dir, args.git_username, args.git_password)
        else:
            repo_path = args.repo
            if not os.path.isdir(repo_path):
                sys.exit(f"[!] Path repo tidak ditemukan: {repo_path}")

        final_readme = run_pipeline(repo_path, args.lang)

        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(final_readme)
        print(f"[✓] README.md berhasil dibuat: {out_path}")

    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
