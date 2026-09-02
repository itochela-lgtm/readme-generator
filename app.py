#!/usr/bin/env python3
"""
Streamlit UI - README Generator (LangGraph + DashScope)
"""

import os
import shutil
import tempfile

import streamlit as st

from generate_readme import build_graph, clone_repo, run_pipeline, MODEL_NAME

st.set_page_config(page_title="README Generator", page_icon="📝", layout="wide")

st.title("📝 README Generator")
st.caption(f"LangGraph + DashScope (model: `{MODEL_NAME}`) — auto-generate README.md from a local or git repo")

if not os.getenv("DASHSCOPE_API_KEY"):
    st.error("ENV `DASHSCOPE_API_KEY` is not set. Check your `.env` file.")
    st.stop()

mode = st.radio("Repo source", ["Local repo (path inside container)", "External repo (git URL)"], horizontal=True)
lang_choice = st.selectbox("README language", ["English", "Bahasa Indonesia"], index=0)
lang_code = "en" if lang_choice == "English" else "id"

repo_input = None
if mode.startswith("Local repo"):
    repo_input = st.text_input(
        "Repo path (must already be mounted into the container)",
        value="/workspace/repo",
        help="This path refers to inside the container, matching the volume mount in docker-compose.yml",
    )
else:
    repo_input = st.text_input(
        "Git URL",
        placeholder="https://github.com/user/project.git",
    )
    with st.expander("🔒 Private repo credentials (optional)"):
        st.caption("Leave blank for public repos. Clear these if the URL is on a different host than your default .env credentials.")
        git_username = st.text_input("Username", value=os.getenv("GIT_USERNAME", ""), key="git_username")
        git_password = st.text_input("Password / Access Token", value=os.getenv("GIT_TOKEN", ""), type="password", key="git_password")

generate_btn = st.button("🚀 Generate README", type="primary")

if "readme_result" not in st.session_state:
    st.session_state.readme_result = None

if generate_btn:
    if not repo_input:
        st.warning("Fill in the repo path/URL first.")
        st.stop()

    tmp_dir = None
    try:
        with st.spinner(f"Scanning repo & generating README via {MODEL_NAME}..."):
            if mode.startswith("External repo"):
                tmp_dir = tempfile.mkdtemp(prefix="readme-src-")
                repo_path = clone_repo(
                    repo_input,
                    tmp_dir,
                    st.session_state.get("git_username") or None,
                    st.session_state.get("git_password") or None,
                )
            else:
                if not os.path.isdir(repo_input):
                    st.error(f"Path not found inside the container: {repo_input}")
                    st.stop()
                repo_path = repo_input

            st.session_state.readme_result = run_pipeline(repo_path, lang_code)
    except Exception as e:
        st.error(f"Generation failed: {e}")
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)

if st.session_state.readme_result:
    st.success("README generated successfully.")
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
