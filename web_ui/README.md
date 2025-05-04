# OWLBEAR Web UI

A web-based user interface for the OWLBEAR (Orchestrated Workflow Logic with Bespoke Experts for Agentic Routines) framework.

## Overview

This UI provides a simple way to:
- Browse available workflows
- Execute workflows with custom parameters
- Monitor workflow execution in real-time
- Visualize expert interactions
- Track tool calls and execution logs

## Architecture

The web UI consists of:

1. **Backend (FastAPI)** - Provides API endpoints and WebSocket connections to interact with OWLBEAR
2. **Frontend (HTML/JS)** - Simple interface for selecting and executing workflows, monitoring execution, and visualizing experts

## Setup & Installation

1. Install the requirements:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
cd /path/to/OWLBEAR
python -m web_ui.main
```

3. Access the UI in your browser:
```
http://localhost:8000
```

## API Endpoints

The following API endpoints are available:

### Workflows
- `GET /api/workflows` - List all available workflows
- `GET /api/workflows/{workflow_id}` - Get workflow details
- `POST /api/workflows/{workflow_id}/execute` - Execute a workflow
- `POST /api/workflows/{workflow_id}/cancel` - Cancel a running workflow

### Experts
- `GET /api/experts` - List all available experts
- `GET /api/experts/{expert_id}` - Get expert details

### Executions
- `GET /api/executions` - List recent workflow executions
- `GET /api/executions/{execution_id}` - Get execution details

### WebSockets
- `/ws/execution/{execution_id}` - Real-time updates for workflow execution

## Message Types

The WebSocket connection provides several message types:

- `log` - Log messages from the workflow execution
- `step_update` - Updates about the current step in the workflow
- `tool_call` - Information about tool calls made by experts
- `execution_status` - Status updates for the workflow execution
- `error` - Error messages

## Integration with OWLBEAR

The UI integrates with OWLBEAR by:

1. Reading workflow YAML files from the OWLBEAR workflows directory
2. Reading expert configurations from the OWLBEAR experts directory
3. Executing workflows through the OWLBEAR engine
4. Monitoring execution logs and outputs

## Development

To modify the UI:
- Backend code is in the `services` directory
- Frontend code is in the `static` directory
