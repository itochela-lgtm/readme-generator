# README Generator

A CLI and Streamlit web UI for generating `README.md` files from local or remote Git repositories using LangGraph and DashScope.

## Description

This project provides a tool that scans a repository and produces a README file. It can be used either as a command-line utility or through a Streamlit interface. The generator supports local repositories mounted into a Docker container and external Git repositories accessed by URL.

## Key Features

- Generate `README.md` from a local repository path.
- Generate `README.md` from an external Git repository URL.
- Streamlit UI for selecting repository source, language, and running generation.
- Language selection for generated README:
  - English
  - Bahasa Indonesia
- CLI mode using `generate_readme.py`.
- Docker and Docker Compose support.
- Optional private Git repository credentials via environment variables or UI inputs.
- Output can be written to a mounted output directory when running in Docker.

## Tech Stack

- Python 3.11
- Streamlit
- LangGraph
- LangChain Core
- LangChain OpenAI integration
- LangChain Anthropic integration
- LangChain Google GenAI integration
- GitPython
- python-dotenv
- DashScope API, configured through `DASHSCOPE_API_KEY`

## Installation

### Prerequisites

- Python 3.11 or compatible environment for local execution
- Docker and Docker Compose for containerized execution
- A valid DashScope API key

### Local Python Setup

```bash
git clone <repository-url>
cd <repository-directory>

python -m venv .venv
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
```

Create an environment file:

```bash
cp .env.example .env
```

Set the required API key in `.env`:

```env
DASHSCOPE_API_KEY=your-dashscope-api-key
```

Optional Git credentials for private repositories:

```env
GIT_USERNAME=your-git-username
GIT_TOKEN=your-git-token-or-password
```

### Docker Setup

Build the image:

```bash
docker build -t readme-generator:latest .
```

Or build through Docker Compose:

```bash
docker compose build
```

## Usage

### CLI Usage

Show CLI help:

```bash
python generate_readme.py --help
```

Generate a README from a local repository:

```bash
python generate_readme.py --repo /path/to/repo --output README.md
```

### Docker CLI Usage

The Docker Compose CLI service mounts the local repository into `/workspace/repo` and writes the generated file to `./output/README.md`.

Set the repository path:

```bash
export LOCAL_REPO_PATH=/path/to/repo
```

Run the CLI generator:

```bash
docker compose --profile cli run --rm readme-generator
```

The generated README will be available at:

```text
./output/README.md
```

Alternatively, run the image directly:

```bash
docker run --rm \
  -e DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY" \
  -v /path/to/repo:/workspace/repo:ro \
  -v "$(pwd)/output:/output" \
  readme-generator:latest \
  python generate_readme.py --repo /workspace/repo --output /output/README.md
```

### Streamlit UI Usage

Run locally:

```bash
streamlit run app.py
```

Then open the Streamlit URL shown in the terminal, usually:

```text
http://localhost:8501
```

Run with Docker Compose:

```bash
docker compose up readme-ui
```

Then open:

```text
http://localhost:8501
```

In the UI:

1. Select the repository source:
   - **Local repo**: provide a path inside the container, for example `/workspace/repo`
   - **External repo**: provide a Git URL
2. Select the README language.
3. Click **Generate README**.

For Docker usage with a local repository, mount the repository using `LOCAL_REPO_PATH`:

```bash
LOCAL_REPO_PATH=/path/to/repo docker compose up readme-ui
```

Inside the UI, use the container path:

```text
/workspace/repo
```

For external repositories, private repository credentials can be provided optionally:

- `GIT_USERNAME`
- `GIT_TOKEN`

## Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `DASHSCOPE_API_KEY` | Yes | API key used by the README generation pipeline. |
| `GIT_USERNAME` | No | Username for private Git repositories. |
| `GIT_TOKEN` | No | Password or access token for private Git repositories. |
| `LOCAL_REPO_PATH` | No | Host path mounted into `/workspace/repo` by Docker Compose. |

## Project Structure

```text
.
├── .env.example          # Example environment variables
├── .gitignore            # Git ignore rules
├── Dockerfile            # Container image definition
├── LICENSE               # License information
├── app.py                # Streamlit UI
├── docker-compose.yml    # CLI and UI service definitions
├── generate_readme.py    # Core generation logic and CLI entrypoint
└── requirements.txt      # Python dependencies
```

## Docker Notes

The `Dockerfile` configures Aliyun mirrors for apt and pip to improve download speed in certain network environments. If you are running outside of such an environment, you may remove or replace those mirror settings.

## License

See the `LICENSE` file for details.
