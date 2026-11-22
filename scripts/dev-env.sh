# Source this in WSL:  source scripts/dev-env.sh
# Local development environment: Chroma in Docker on :8000, Ollama on :11434.
export PYTHONPATH="$PWD:$PWD/indexer:$PWD/api"
export PY="$HOME/rahbar-venv/bin/python"
export CHROMA_HOST=localhost CHROMA_PORT=8000 CHROMA_COLLECTION="${CHROMA_COLLECTION:-rahbar}"
export OLLAMA_URL=http://localhost:11434 EMBED_MODEL=nomic-embed-text
export CHUNK_SIZE="${CHUNK_SIZE:-400}" CHUNK_OVERLAP="${CHUNK_OVERLAP:-50}"
export RAGOPS_ROLE="${RAGOPS_ROLE:-ingestor}"
export RAGOPS_DATA_DIR="$PWD/data"
