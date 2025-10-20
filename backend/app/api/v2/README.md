# API v2 - Deep Research Routes

RESTful API with WebSocket streaming for AI-powered deep research workflows.

## Overview

API v2 provides endpoints for:
- **Starting research workflows** - Initiate long-running AI-powered case analysis
- **Monitoring progress** - Real-time status updates via REST or WebSocket
- **Managing workflows** - Pause, resume, cancel running research
- **Retrieving results** - Access findings, dossiers, and citations

## Architecture

```
/api/v2/
├── research/                    # Research workflow endpoints
│   ├── POST /                   # Start new research
│   ├── GET /{id}/status        # Get status
│   ├── POST /{id}/pause        # Pause workflow
│   ├── POST /{id}/resume       # Resume workflow
│   ├── POST /{id}/cancel       # Cancel workflow
│   ├── GET /{id}/findings      # Get findings
│   ├── GET /{id}/dossier       # Get dossier
│   └── GET /{id}/dossier/download  # Download file
├── research/{id}/stream         # WebSocket for real-time updates
└── cases/{id}/research          # List research runs for case
```

## Quick Start

### 1. Start a Research Workflow

```bash
curl -X POST http://localhost:8000/api/v2/research \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "01234567890123456789ab",
    "query": "Identify timeline of communications regarding contract negotiation",
    "defense_theory": "Client acted in good faith based on available information"
  }'
```

Response:
```json
{
  "research_run_id": "research_abc123def456",
  "workflow_id": "deep-research-research_abc123def456",
  "message": "Research workflow started successfully",
  "status_url": "/api/v2/research/research_abc123def456/status",
  "websocket_url": "/api/v2/research/research_abc123def456/stream"
}
```

### 2. Monitor Progress (REST Polling)

```bash
curl http://localhost:8000/api/v2/research/research_abc123def456/status
```

Response:
```json
{
  "research_run_id": "research_abc123def456",
  "case_id": "01234567890123456789ab",
  "workflow_id": "deep-research-research_abc123def456",
  "status": "RUNNING",
  "phase": "DOCUMENT_ANALYSIS",
  "progress_pct": 45.0,
  "query": "Identify timeline of communications...",
  "defense_theory": null,
  "findings_count": 23,
  "citations_count": 67,
  "current_activity": "run_document_analysis",
  "is_paused": false,
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": null,
  "estimated_completion": "2024-01-15T12:00:00Z",
  "errors": []
}
```

### 3. Monitor Progress (WebSocket Streaming)

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/research/research_abc123def456/stream');

ws.onopen = () => {
  console.log('Connected to research stream');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(`${message.type}: ${message.data.phase} - ${message.data.progress_pct}%`);

  if (message.type === 'completed') {
    console.log('Research completed!');
    ws.close();
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

WebSocket message types:
- `status` - Initial status when connecting
- `progress` - Progress updates (every 2 seconds)
- `phase_change` - Workflow entered new phase
- `finding` - New finding discovered (future)
- `completed` - Workflow completed successfully
- `error` - Workflow failed or error occurred

### 4. Control Workflow

Pause:
```bash
curl -X POST http://localhost:8000/api/v2/research/research_abc123def456/pause
```

Resume:
```bash
curl -X POST http://localhost:8000/api/v2/research/research_abc123def456/resume
```

Cancel:
```bash
curl -X POST http://localhost:8000/api/v2/research/research_abc123def456/cancel
```

### 5. Retrieve Results

Get findings:
```bash
curl http://localhost:8000/api/v2/research/research_abc123def456/findings?limit=50
```

Get dossier:
```bash
curl http://localhost:8000/api/v2/research/research_abc123def456/dossier
```

Download dossier file:
```bash
curl -O http://localhost:8000/api/v2/research/research_abc123def456/dossier/download?format=pdf
```

## Research Workflow Phases

1. **INITIALIZING** (0-5%) - Setting up research run
2. **DISCOVERY** (5-15%) - Case cartography, inventory evidence
3. **PLANNING** (15-25%) - Generate search strategies
4. **DOCUMENT_ANALYSIS** (25-40%) - Analyze documents in parallel
5. **TRANSCRIPT_ANALYSIS** (25-40%) - Analyze transcripts in parallel
6. **COMMUNICATION_ANALYSIS** (25-40%) - Analyze communications in parallel
7. **CORRELATION** (60-75%) - Build knowledge graph, detect patterns
8. **SYNTHESIS** (75-90%) - Generate dossier with findings
9. **REPORT_GENERATION** (90-100%) - Create PDF/DOCX files
10. **COMPLETED** (100%) - Research finished

## Workflow States

- **PENDING** - Workflow queued, not yet started
- **RUNNING** - Workflow actively executing
- **COMPLETED** - Workflow finished successfully
- **FAILED** - Workflow encountered an error
- **CANCELLED** - Workflow cancelled by user

## Finding Types

Findings are categorized by type:
- **FACT** - Factual statement backed by evidence
- **PATTERN** - Recurring theme or behavior
- **ANOMALY** - Unusual or unexpected observation
- **RELATIONSHIP** - Connection between entities
- **TIMELINE_EVENT** - Timestamped event
- **CONTRADICTION** - Conflicting information
- **CORROBORATION** - Supporting evidence
- **GAP** - Missing information

## Error Handling

All endpoints use standard HTTP status codes:
- **200 OK** - Request succeeded
- **202 Accepted** - Workflow started/action accepted
- **400 Bad Request** - Invalid parameters
- **404 Not Found** - Resource not found
- **500 Internal Server Error** - Server error

Error responses include a `detail` field:
```json
{
  "detail": "Research run not found or workflow unavailable"
}
```

## Rate Limiting

Research workflows are resource-intensive. Recommended limits:
- Max 5 concurrent research runs per case
- Max 10 concurrent research runs per user
- Poll status endpoint max every 2 seconds
- Use WebSocket for real-time updates instead of polling

## Implementation Status

### ✅ Implemented
- Research workflow orchestration (Temporal)
- Start research endpoint
- Status query endpoint
- Pause/resume/cancel signals
- WebSocket streaming
- Phase tracking
- Progress calculation

### 🚧 In Progress
- Findings retrieval from storage
- Dossier retrieval
- File download
- Research run listing

### 📋 Planned
- Real-time finding broadcasts via WebSocket
- Advanced filtering and search
- Export formats (JSON, Markdown)
- Webhook notifications

## Architecture Notes

### RESTful Design
- Proper HTTP methods (GET, POST)
- Appropriate status codes (202 for async operations)
- Resource-oriented URLs
- Idempotent operations where possible

### WebSocket Protocol
- Connection per research run
- Server-initiated messages only
- Client can disconnect anytime
- Auto-cleanup on completion

### Workflow Integration
- Direct integration with Temporal workflows
- Query workflow state via Temporal client
- Send signals (pause/resume/cancel)
- Long-running operation support (hours)

### Type Safety
- Pydantic schemas for validation
- OpenAPI documentation
- Type hints throughout

## Development

### Files
- `routes/research.py` - REST endpoint handlers
- `websockets/research_stream.py` - WebSocket endpoint
- `schemas/research.py` - Pydantic request/response models
- `router.py` - Router aggregation

### Testing
```bash
# Unit tests
mise run test app/api/v2/

# Integration tests with running Temporal
mise run test:integration

# Manual testing
mise run up:backend
curl http://localhost:8000/api/v2/research
```

### Documentation
- OpenAPI schema: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Examples

See [examples/](./examples/) directory for:
- Python client usage
- JavaScript/TypeScript WebSocket client
- Complete workflow examples
- Error handling patterns

## Support

For questions or issues:
1. Check OpenAPI docs at `/api/docs`
2. Review workflow logs in Temporal UI
3. Examine backend logs: `mise run logs:backend`
