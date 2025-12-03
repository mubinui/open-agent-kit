# RAG (Retrieval-Augmented Generation) Setup Guide

This guide covers the complete setup and configuration of the RAG Pipeline with Qdrant vector database for the Orchestration Service.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Configuration](#configuration)
- [Document Ingestion](#document-ingestion)
- [Using RAG in Workflows](#using-rag-in-workflows)
- [Admin UI Management](#admin-ui-management)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Orchestration Service integrates with a **remote RAG Pipeline service** for document processing, embedding generation, and semantic search capabilities. This enables agents to access and query knowledge bases using natural language.

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **RAG Pipeline Service** | Document ingestion, embedding, search | `http://10.42.65.199:8000` (remote) |
| **Qdrant Vector DB** | Vector storage and similarity search | `localhost:6333` (local/docker) |
| **Orchestration Service** | Agent workflows and RAG tools | `localhost:8000` |
| **Admin UI** | Visual management interface | `localhost:4200` |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │   Admin UI   │  │   REST API   │  │   Agent Workflows  │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└────────────────────────────┬─────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
┌───────────────▼──────────┐  ┌──────────▼──────────────────┐
│  Orchestration Service   │  │  RAG Pipeline Service       │
│  (localhost:8000)        │  │  (10.42.65.199:8000)        │
│                          │  │                              │
│  • RAG Tools            │──▶│  • Document Processing       │
│  • Agent Orchestration  │  │  • Embedding Generation      │
│  • Workflow Engine      │  │  • Semantic Search           │
└──────────────────────────┘  └──────────┬──────────────────┘
                                         │
                             ┌───────────▼───────────┐
                             │   Qdrant Vector DB    │
                             │   (localhost:6333)    │
                             │                        │
                             │  • Vector Storage      │
                             │  • Similarity Search   │
                             └────────────────────────┘
```

---

## Prerequisites

### Required

- **Docker & Docker Compose** - For running Qdrant locally
- **Python 3.11+** - For the orchestration service
- **Network Access** - To reach `http://10.42.65.199:8000` (RAG Pipeline)

### Optional

- **Node.js 18+** - For Admin UI development
- **kubectl & Helm** - For Kubernetes deployment

---

## Local Development Setup

### 1. Start Qdrant Vector Database

```bash
# Option A: Using the helper script
./scripts/start_qdrant_docker.sh

# Option B: Using docker-compose (recommended)
docker-compose up -d qdrant

# Verify Qdrant is running
curl http://localhost:6333/readyz

# Access Qdrant dashboard
open http://localhost:6333/dashboard
```

### 2. Configure Environment Variables

Create or update `.env` file:

```bash
# Copy from example
cp .env.example .env

# Edit with your values
# Required RAG Pipeline Configuration
RAG_PIPELINE_BASE_URL=http://10.42.65.199:8000
RAG_PIPELINE_ENABLED=true
RAG_PIPELINE_TIMEOUT=60
RAG_PIPELINE_API_KEY=                    # Set if service requires auth
RAG_PIPELINE_DEFAULT_COLLECTION=knowledge_base

# Qdrant Configuration (local instance)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=                          # Optional, for production
QDRANT_COLLECTION=rag_documents

# LLM Provider (required for agents)
OPENROUTER_API_KEY=your_api_key_here
```

### 3. Start the Orchestration Service

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the API server
uvicorn src.api.main:app --reload --port 8000

# Verify the service
curl http://localhost:8000/health
```

### 4. Verify RAG Pipeline Connectivity

```bash
# Check RAG Pipeline health
curl http://10.42.65.199:8000/health

# View API documentation
open http://10.42.65.199:8000/docs
```

---

## Configuration

### Vector Database Configuration

Edit `configs/vector_databases.json`:

```json
{
  "version": "1.0",
  "qdrant": {
    "type": "qdrant",
    "config": {
      "host": "localhost",
      "port": 6333,
      "collection_name": "rag_documents",
      "embedding_model": "all-mpnet-base-v2",
      "embedding_dimensions": 768,
      "distance_metric": "cosine",
      "api_key": null,
      "prefer_grpc": false,
      "timeout": 60
    }
  }
}
```

### RAG Tools Configuration

The following tools are pre-configured in `configs/tools.json`:

- `rag_query` - Search the knowledge base
- `rag_ingest_file` - Upload documents
- `rag_list_files` - List documents in a collection
- `rag_delete_file` - Remove documents
- `rag_get_stats` - Get collection statistics

### RAG Agents Configuration

Two agents are pre-configured in `configs/agents.json`:

1. **`rag_assistant`** - General RAG agent with query capabilities
2. **`rag_knowledge_agent`** - Specialized knowledge retrieval agent

### RAG Workflows Configuration

Two workflows are available in `configs/workflows.json`:

1. **`rag_qa_assistant`** - Simple Q&A using RAG
2. **`rag_research_workflow`** - Multi-step research with reasoning

---

## Document Ingestion

### Using the Ingestion Script

The `scripts/ingest_rag_documents.py` script uploads documents to the remote RAG Pipeline service.

#### Single File Ingestion

```bash
python scripts/ingest_rag_documents.py \
  --file /path/to/document.pdf \
  --collection knowledge_base
```

#### Directory Ingestion (Recursive)

```bash
python scripts/ingest_rag_documents.py \
  --directory ./docs \
  --collection knowledge_base \
  --recursive
```

#### Batch Ingestion (Multiple Files)

```bash
python scripts/ingest_rag_documents.py \
  --files doc1.pdf doc2.txt doc3.md \
  --collection knowledge_base \
  --batch
```

#### View Collection Statistics

```bash
python scripts/ingest_rag_documents.py \
  --file document.pdf \
  --collection knowledge_base \
  --stats
```

### Supported File Formats

- PDF (`.pdf`)
- Text (`.txt`, `.md`)
- Word Documents (`.docx`)
- HTML (`.html`)
- JSON (`.json`)

---

## Using RAG in Workflows

### Create a RAG Session

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "rag_qa_assistant",
    "user_id": "test_user"
  }'
```

### Query the Knowledge Base

```bash
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the key features of our product?"
  }'
```

### Example: Research Workflow

```bash
# Use the research workflow for multi-step queries
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "rag_research_workflow"
  }'

# Ask a complex question
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Compare the performance metrics from Q3 and Q4 reports"
  }'
```

---

## Admin UI Management

### Starting the Admin UI

```bash
cd admin-ui
npm install
npm start

# Access at http://localhost:4200
```

### Vector DB Page

Navigate to **Vector DB** in the sidebar to:

- View all configured vector databases
- Check connection status
- View collection details (name, model, dimensions)
- Monitor Qdrant configuration

### Testing RAG Workflows

1. Go to the **Testing** page
2. Select a RAG workflow (`rag_qa_assistant` or `rag_research_workflow`)
3. Create a session
4. Send messages to query the knowledge base
5. View conversation history and agent responses

---

## Production Deployment

### Kubernetes/Helm Deployment

The Helm chart includes Qdrant as a local service but connects to the remote RAG Pipeline.

```bash
# Install the chart
helm install orchestration-service ./helm/orchestration-service \
  --set secrets.openrouterApiKey=your_key \
  --set ragPipeline.baseUrl=http://10.42.65.199:8000 \
  --set qdrant.enabled=true

# Verify deployment
kubectl get pods -l app=orchestration-service
kubectl logs -l app=orchestration-service -f
```

### Environment Variables

For production, ensure these are set:

```bash
# RAG Pipeline (External Service)
RAG_PIPELINE_BASE_URL=http://10.42.65.199:8000
RAG_PIPELINE_ENABLED=true
RAG_PIPELINE_API_KEY=production_api_key_here
RAG_PIPELINE_DEFAULT_COLLECTION=production_kb

# Qdrant (Cluster or Managed Instance)
QDRANT_URL=http://qdrant-cluster:6333
QDRANT_API_KEY=production_qdrant_key
QDRANT_COLLECTION=production_documents
```

### Security Considerations

1. **API Key Management** - Store RAG_PIPELINE_API_KEY in secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
2. **Network Security** - Ensure secure communication between services (VPN, private network)
3. **Access Control** - Implement RBAC for document ingestion and query operations
4. **Data Encryption** - Use TLS/SSL for all API calls to the RAG Pipeline

---

## Troubleshooting

### RAG Pipeline Connection Issues

```bash
# Test RAG Pipeline connectivity
curl -v http://10.42.65.199:8000/health

# Check if firewall/network allows access
telnet 10.42.65.199 8000

# Verify environment variables
echo $RAG_PIPELINE_BASE_URL
```

### Qdrant Connection Issues

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Test Qdrant API
curl http://localhost:6333/collections

# View Qdrant logs
docker logs orchestration-qdrant
```

### Document Ingestion Failures

```bash
# Check ingestion script logs
python scripts/ingest_rag_documents.py --file test.pdf --collection test --verbose

# Verify file format is supported
file test.pdf

# Check RAG Pipeline logs (if accessible)
curl http://10.42.65.199:8000/stats
```

### Agent Query Failures

```bash
# Check if RAG tools are loaded
curl http://localhost:8000/api/v1/tools | jq '.[] | select(.id | startswith("rag"))'

# Verify workflow configuration
curl http://localhost:8000/api/v1/workflows/rag_qa_assistant

# Check agent logs
tail -f logs/orchestration.log | grep rag
```

### Empty Search Results

- Verify documents are ingested: Use `--stats` flag with ingestion script
- Check collection name matches: `QDRANT_COLLECTION` must match `RAG_PIPELINE_DEFAULT_COLLECTION`
- Confirm embedding model consistency: Both Qdrant and RAG Pipeline should use the same model
- Test with direct Qdrant API: `curl http://localhost:6333/collections/rag_documents/points/scroll`

---

## Additional Resources

- **RAG Pipeline Swagger**: http://10.42.65.199:8000/docs
- **Qdrant Documentation**: https://qdrant.tech/documentation/
- **Orchestration Service API**: http://localhost:8000/docs
- **Admin UI**: http://localhost:4200

For more help, check the main [README.md](../README.md) or open an issue in the repository.
