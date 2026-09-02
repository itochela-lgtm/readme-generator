#!/usr/bin/env python3
"""
Streamlit UI - README Generator (LangGraph + DashScope qwen3.6-plus)
"""

import os
import shutil
import tempfile

import streamlit as st

from generate_readme import build_graph, clone_repo, run_pipeline, MODEL_NAME

st.set_page_config(page_title="README Generator", page_icon="📝", layout="wide")

st.title("📝 README Generator")
st.caption(f"LangGraph + DashScope (model: `{MODEL_NAME}`) — auto-generate README.md dari repo lokal atau git URL")

if not os.getenv("DASHSCOPE_API_KEY"):
    st.error("ENV `DASHSCOPE_API_KEY` belum di-set. Cek file `.env` kamu.")
    st.stop()

mode = st.radio("Sumber repo", ["Repo lokal (path di dalam container)", "Repo eksternal (git URL)"], horizontal=True)
lang_choice = st.selectbox("Bahasa README", ["Bahasa Indonesia", "English"], index=0)
lang_code = "id" if lang_choice == "Bahasa Indonesia" else "en"

repo_input = None
if mode.startswith("Repo lokal"):
    repo_input = st.text_input(
        "Path repo (harus sudah di-mount ke container)",
        value="/workspace/repo",
        help="Path ini merujuk ke dalam container, sesuaikan dengan volume mount di docker-compose.yml",
    )
else:
    repo_input = st.text_input(
        "Git URL",
        placeholder="https://github.com/user/proyek.git",
    )
    with st.expander("🔒 Kredensial repo private (opsional)"):
        git_username = st.text_input("Username", value=os.getenv("GIT_USERNAME", ""), key="git_username")
        git_password = st.text_input("Password / Access Token", value=os.getenv("GIT_TOKEN", ""), type="password", key="git_password")

generate_btn = st.button("🚀 Generate README", type="primary")

if "readme_result" not in st.session_state:
    st.session_state.readme_result = None

if generate_btn:
    if not repo_input:
        st.warning("Isi path/URL repo dulu.")
        st.stop()

    tmp_dir = None
    try:
        with st.spinner(f"Scanning repo & generating README via {MODEL_NAME}..."):
            if mode.startswith("Repo eksternal"):
                tmp_dir = tempfile.mkdtemp(prefix="readme-src-")
                repo_path = clone_repo(
                    repo_input,
                    tmp_dir,
                    st.session_state.get("git_username") or None,
                    st.session_state.get("git_password") or None,
                )
            else:
                if not os.path.isdir(repo_input):
                    st.error(f"Path tidak ditemukan di dalam container: {repo_input}")
                    st.stop()
                repo_path = repo_input

            st.session_state.readme_result = run_pipeline(repo_path, lang_code)
    except Exception as e:
        st.error(f"Gagal generate: {e}")
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

if st.session_state.readme_result:
    st.success("README berhasil dibuat.")
    st.download_button(
        "⬇️ Download README.md",
        data=st.session_state.readme_result,
        file_name="README.md",
        mime="text/markdown",
    )
    tab_preview, tab_raw = st.tabs(["Preview", "Raw markdown"])
    with tab_preview:
        st.markdown(st.session_state.readme_result)
    with tab_raw:
        st.code(st.session_state.readme_result, language="markdown")
