# KlimtechRAG - Agent Guidelines

## Project Overview
RAG system with Python 3.12, FastAPI, Haystack, and Qdrant. Indexes documents (PDF, text, code, audio, video) with LLM-based query responses.

## Build, Lint, and Test Commands

### Tests
```bash
pytest                        # All tests
pytest backend_app            # Specific directory
pytest backend_app/test_file.py::test_func  # Single test
pytest -k "pattern"           # By pattern
pytest -v                     # Verbose
pytest --cov=backend_app      # Coverage
```

### Linting
```bash
ruff check .                  # Check code quality
ruff check --fix .            # Auto-fix
ruff check --statistics .     # Stats
```

### Formatting
```bash
ruff format .                 # Format code
ruff format --check .         # Check formatting
ruff format --diff .          # Show diff
```

## Code Style

### Python Version
Python 3.12.3

### Type Hints
Use type hints for all function arguments and returns. Import from `typing` when needed.
```python
def is_text_file(file_path: str) -> bool:
    ...
```

### Naming
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_snake_case`

### Imports
Order: standard → third-party → local. Separate groups with blank lines.
```python
import os
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from haystack import Pipeline
```

### Error Handling
Use try-except with print for debugging. Raise HTTPException for API errors. Always cleanup in finally blocks.
```python
try:
    result = pipeline.run(...)
    return {"message": "Success"}
except Exception as e:
    print(f"Error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
finally:
    if temp_file_path and os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
```

### Docstrings/Comments
Triple-quoted docstrings for functions (English for endpoints). Inline comments in Polish.
```python
async def ingest_file(file: UploadFile):
    """Endpoint do ładowania plików PDF do bazy RAG."""
    # 1. Sprawdzenie rozszerzenia pliku
    suffix = os.path.splitext(file.filename)[1].lower()
```

### File Structure
1. Imports
2. Environment variables & constants
3. Helper functions
4. Pipeline/component setup
5. Pydantic models
6. API endpoints
7. Signal handlers
8. Main execution block

### API Endpoints
Use async functions, Pydantic models for requests, HTTPException for errors.
```python
@app.post("/ingest")
async def ingest_file(file: UploadFile):
    try:
        result = process_file(file)
        return {"message": "Success", "chunks": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Project Structure
- `backend_app/main.py` - FastAPI application
- `git_sync/ingest_repo.py` - Git repo sync
- `watch_nextcloud.py` - File system watcher
- `pytest.ini` - Test paths: `backend_app`, `git_sync`; ignore: `data`, `llama.cpp`, `venv`

### Key Tech
FastAPI, Haystack, Qdrant, Pydantic, Docling, Watchdog, pytest, ruff

### Best Practices
1. Clean up temp files in `finally` blocks
2. Validate file extensions/sizes before processing
3. Use meaningful variable names
4. Print debug messages with prefixes: `[DEBUG]`, `[ERROR]`
5. Use environment variables for config
6. Handle signals gracefully

### Testing
Tests in `backend_app/` or `git_sync/`. Files start with `test_` or end with `_test.py`. Use pytest fixtures, test success/error cases, mock external dependencies.

### Common Patterns
- **File processing**: `tempfile.NamedTemporaryFile(delete=False)`, cleanup in `finally`
- **Folder traversal**: `os.walk()` with directory filtering
- **API requests**: `requests.post()` with timeout and error handling
- **Pipeline**: Haystack Pipeline with `connect()` method

### Folder Blacklist
Skip: `node_modules`, `.git`, `__pycache__`, `.venv`, `venv`, `build`, `dist`, `.idea`

### Allowed Extensions
`.pdf`, `.md`, `.txt`, `.py`, `.json`, `.yml`, `.yaml`, `.mp3`, `.mp4`, `.jpeg`, `.jpg`, `.js`, `.ts`

### File Size Limit
Maximum 500 KB. Check with `os.path.getsize()`.

### Running
```bash
cd ~/KlimtechRAG
source venv/bin/activate
python start_klimtech.py
```

### Services
- Backend: http://localhost:8000
- LLM: http://localhost:8082
- Qdrant: http://localhost:6333
