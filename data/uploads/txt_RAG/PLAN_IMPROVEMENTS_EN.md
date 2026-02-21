# KlimtechRAG System Improvement Plan

## Current Architecture Overview

After analyzing the KlimtechRAG project, here is a detailed improvement plan:

### Core System Components

**1. Backend API** (`/home/lobo/KlimtechRAG/backend_app/main.py`)
- FastAPI application running on port 8000
- File ingestion endpoint (`/ingest`) supporting PDF, text, and code files
- RAG query endpoint (`/query`) with web search augmentation
- Code-specific query endpoint (`/code_query`) for developer tasks
- Uses Docling for PDF parsing and SentenceTransformers for embeddings
- Integration with Qdrant vector database and LLM server

**2. LLM Server** - llama.cpp server on port 8081 running LFM2-2.6B model

**3. File Watcher** (`watch_nextcloud.py`) - Monitors Nextcloud folders
- Monitors: Doc_RAG, Audio_RAG, Video_RAG, Images_RAG, json_RAG, pdf_RAG, txt_RAG
- Automatically ingests new files to the RAG system

**4. Git Sync** (`/home/lobo/KlimtechRAG/git_sync/ingest_repo.py`) - Batch repository indexing tool

**5. Orchestration** (`start_klimtech.py`) - Master startup script managing all services

### Data Flow

```
Nextcloud Files → Watchdog → /ingest API → Docling/Parsing → SentenceTransformers → Qdrant
                                                                            ↓
User Query → /query API → Embed Query → Qdrant Retrieval + Web Search → LLM → Response
```

### Core Technologies
- FastAPI, Haystack, Qdrant, Docling, SentenceTransformers, llama.cpp
- Podman containers (Qdrant, Nextcloud, PostgreSQL, n8n)
- Python 3.12.3

---

## Current System Status

### What's Working
- Basic RAG pipeline with document ingestion and querying
- File monitoring for Nextcloud folders
- Git repository batch ingestion capability
- Multi-format support (PDF, audio, video, text, code)
- Service orchestration with health checks

### Issues Found
1. **Code duplication** - `CodeQueryRequest` class is defined twice in main.py (lines 225-226 and 278-279)
2. **Incomplete code** - file appears truncated at line 279
3. **Limited error handling** in some endpoints
4. **No comprehensive test suite** in project root
5. **Potential duplicate code** in main execution block

---

## Recommended Improvement Plan

### Phase 1: Code Quality and Stability

**Goal:** Improve code quality and eliminate bugs

#### 1.1 Code Duplication Fix
- Remove duplicate `CodeQueryRequest` class definition
- Refactor common models into separate module
- Unify data structures in API

#### 1.2 Complete Incomplete Code
- Analyze main.py file for missing fragments
- Add missing imports and functions
- Verify `if __name__ == "__main__"` block consistency

#### 1.3 Error Handling Improvements
- Wrap all API endpoints with proper exception handling
- Add detailed error messages
- Implement error logging with context
- Add HTTP error codes for different scenarios

#### 1.4 Input Validation
- Validate file sizes and types before processing
- Check query parameter correctness
- Limit uploaded file sizes
- Verify file extensions

---

### Phase 2: Testing and Quality Assurance

**Goal:** Create comprehensive test suite

#### 2.1 Unit Tests
- **File ingestion logic tests:**
  - File extension validation
  - File size checking
  - Various format parsing tests
  - Invalid file handling

- **Query processing tests:**
  - Correct query formatting
  - LLM response validation
  - Web search integration

- **File type validation tests:**
  - Format recognition
  - Unsupported type handling
  - Content validation

- **Error scenario tests:**
  - Non-existent files
  - Qdrant connection errors
  - LLM server issues
  - Timeouts and exceeded limits

#### 2.2 Integration Tests
- **API endpoint tests:**
  - `/ingest` - file upload and processing
  - `/query` - RAG query handling
  - `/code_query` - programming queries
  - Authentication and authorization tests (if implemented)

- **Database connectivity tests:**
  - Qdrant connection
  - CRUD operations on documents
  - Vector search

- **Service health tests:**
  - Endpoint health checks
  - LLM server availability
  - Connection status

#### 2.3 Code Quality Automation
- CI/CD configuration with automatic test execution
- Linting integration in commit process
- Code coverage checking
- Automatic formatting according to standards

---

### Phase 3: Performance Optimization

**Goal:** Increase system performance

#### 3.1 Async Processing
- Refactor file ingestion to async
- Parallel processing of multiple files
- Queue long-running tasks
- Thread utilization optimization

#### 3.2 Batch Processing
- Implement batch processing for large files
- Group Qdrant queries
- Embedding caching
- LLM query optimization

#### 3.3 Caching System
- Cache frequent queries
- Store embedding results
- Cache configuration and metadata
- Cache invalidation strategy

#### 3.4 Embedding Generation Optimization
- Batch processing for multiple documents
- GPU utilization (if available)
- Embedding model compression
- Lazy model initialization

---

### Phase 4: Feature Enhancements

**Goal:** Add new features to the system

#### 4.1 API Security
- User authentication implementation
- Authorization and role system
- Rate limiting for endpoints
- DoS attack protection
- Communication encryption

#### 4.2 Monitoring and Metrics
- System status endpoints
- Performance metrics (latency, throughput)
- Administrative dashboard
- Problem alerting
- Monitoring system integration

#### 4.3 Advanced RAG Features
- Multiple document collections (different sources)
- Metadata filtering
- Result reranking
- Contextual suggestions
- Conversation history

#### 4.4 User Interface
- Web panel for document management
- Query testing interface
- System metrics visualization
- GUI configuration

---

### Phase 5: Documentation and Maintenance

**Goal:** Ensure ease of system maintenance

#### 5.1 API Documentation
- Complete OpenAPI/Swagger documentation
- Usage examples for each endpoint
- Error code descriptions
- API versioning

#### 5.2 Deployment Guides
- Instructions for different environments
- Environment variable configuration
- Backup and restore procedures
- Horizontal scaling

#### 5.3 Troubleshooting
- Common errors and solutions
- Diagnostic procedures
- Log analysis
- Technical support contact

#### 5.4 Logging Configuration
- Log aggregation
- Formatting and log levels
- Log rotation
- Logging system integration

---

## Implementation Timeline

| Phase | Priority | Duration | Main Goals |
|-------|----------|----------|------------|
| Phase 1 | Critical | 1-2 weeks | Stability and critical fixes |
| Phase 2 | High | 2-3 weeks | Quality assurance |
| Phase 3 | Medium | 3-4 weeks | Performance |
| Phase 4 | Optional | 4-6 weeks | New features |
| Phase 5 | Ongoing | Current | Documentation |

---

## Prerequisites Before Starting

### Prerequisites
1. Access to development environment
2. Permissions to modify project files
3. Access to test server
4. Backup of current configuration

### Dependencies to Install
- pytest and fixtures
- Mocking libraries
- Code coverage analysis tools
- CI/CD server (optional)

---

## Next Steps

### Before Implementation

1. **Priority Confirmation:**
   - Which phase is most important to you?
   - Are all phases needed?
   - Are there additional requirements?

2. **Environment Verification:**
   - Do I have full code access?
   - Can I run tests?
   - Is test environment available?

3. **Time Expectations:**
   - When do you plan to have the system ready?
   - Are there any deadlines?
   - Can I work on multiple phases in parallel?

---

## Questions for Clarification

1. **Do you want me to continue with this task list?** If so, from which phase?

2. **Are there any specific problems** you want me to fix first?

3. **Do you need additional features** not included in this plan?

4. **Do you have preferences** for test tools or documentation format?

5. **Would you like progress reports** after completing each phase?

---

## Project Information

- **Location:** `/home/lobo/KlimtechRAG`
- **Python:** 3.12.3
- **Main files:** `backend_app/main.py`, `watch_nextcloud.py`, `git_sync/ingest_repo.py`
- **Tests:** Configuration in `pytest.ini` (ignore: data, llama.cpp, venv)
- **Linting:** `ruff check .` and `ruff format .`

---

*Creation Date: 2026-02-08*
*Version: 1.0*
