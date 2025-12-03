# Orchestration Service - Agent Builder

Modern Angular web interface for managing and testing the Orchestration Service, built with Angular 20 and Angular Material.

## Features

- **Dashboard** - Service metrics, active sessions, system health
- **Agents** - Create, edit, and manage conversable agents
- **Tools** - Configure and test agent tools
- **Workflows** - Design multi-agent conversation workflows
- **RAG Service** - Monitor remote RAG Pipeline service for document retrieval
- **Testing** - Interactive conversation tester with real-time responses
- **Monitoring** - Request logs, performance metrics, error tracking

## Prerequisites

- Node.js 18+ and npm
- Running Orchestration Service API at `http://localhost:8000`

## Development server

### 1. Configure API Connection

The Admin UI connects to the backend API. By default, it uses the proxy configuration in `proxy.conf.json`:

```json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  },
  "/health": {
    "target": "http://localhost:8000",
    "secure": false
  }
}
```

If your API is running on a different host/port, update `proxy.conf.json` accordingly.

### 2. Install Dependencies

```bash
npm install
```

### 3. Start Development Server

```bash
ng serve
# or
npm start
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Using the Agent Builder

### RAG Service Management

The **RAG Service** page (accessible from the sidebar) displays the remote RAG Pipeline service status:

1. Navigate to **RAG Service** in the sidebar
2. View service status card showing:
   - Service health (healthy/unhealthy/unreachable)
   - Base URL and connection settings
   - Available collections
   - Health details for vector DB, embeddings, and reranker
3. Click **API Docs** to open Swagger documentation
4. Click **Refresh Status** to reload service information

**Note**: The RAG service is configured in `configs/vector_databases.json` and uses environment variables from `.env` (RAG_PIPELINE_BASE_URL, etc.). The remote service manages all vector DB operations internally.

### Testing RAG Workflows

1. Go to the **Testing** page
2. Select a workflow from the dropdown:
   - `rag_qa_assistant` - Simple Q&A using RAG
   - `rag_research_workflow` - Multi-step research with reasoning
   - Other custom workflows
3. Click **Create Session** to start a new conversation
4. Enter queries like:
   - "What are the key features in our documentation?"
   - "Summarize the Q3 performance reports"
5. View agent responses with RAG-retrieved context

### Monitoring RAG Operations

- **Dashboard**: Shows metrics for RAG queries, ingestion operations, and vector DB health
- **Agents Page**: View `rag_assistant` and `rag_knowledge_agent` configurations
- **Tools Page**: See RAG tools (`rag_query`, `rag_ingest_file`, etc.)

## Environment Configuration

### API Base URL

For production or custom API endpoints, set the `API_BASE_URL` environment variable:

```bash
# Development (default via proxy)
ng serve

# Custom API endpoint
API_BASE_URL=http://api.example.com ng serve

# Production build with custom API
ng build --configuration production
```

For production builds, update `src/environments/environment.prod.ts`:

```typescript
export const environment = {
  production: true,
  apiBaseUrl: 'https://api.orchestration.example.com'
};
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

### Production Build

```bash
# Build for production
ng build --configuration production

# Output will be in dist/admin-ui/browser/

# Serve with a static file server
npx http-server dist/admin-ui/browser -p 8080
```

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Troubleshooting

### API Connection Issues

If the UI cannot connect to the backend:

1. Verify the Orchestration Service is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check the proxy configuration in `proxy.conf.json`

3. Verify CORS settings on the backend (`.env`):
   ```bash
   CORS_ORIGINS=http://localhost:4200,http://localhost:3000
   ```

4. Check browser console for CORS or network errors

### RAG Service Page Shows Errors

1. Verify RAG Pipeline service is reachable:
   ```bash
   curl http://10.42.65.199:8000/health
   ```

2. Check environment variables in the backend `.env`:
   ```bash
   RAG_PIPELINE_BASE_URL=http://10.42.65.199:8000
   RAG_PIPELINE_ENABLED=true
   ```

3. Verify the `/api/v1/rag-service` endpoint returns data:
   ```bash
   curl http://localhost:8000/api/v1/rag-service
   ```

4. Check backend logs for connectivity issues

### RAG Workflows Not Working

1. Verify RAG Pipeline service is reachable:
   ```bash
   curl http://10.42.65.199:8000/health
   ```

2. Check environment variables in the backend `.env`:
   ```bash
   RAG_PIPELINE_BASE_URL=http://10.42.65.199:8000
   RAG_PIPELINE_ENABLED=true
   ```

3. Ensure Qdrant is running:
   ```bash
   curl http://localhost:6333/readyz
   ```

## Additional Resources

- [Orchestration Service API Docs](http://localhost:8000/docs)
- [RAG Pipeline Swagger](http://10.42.65.199:8000/docs)
- [RAG Setup Guide](../docs/RAG_SETUP.md)
- [Angular CLI Documentation](https://angular.dev/tools/cli)
- [Angular Material Components](https://material.angular.io/components/categories)

