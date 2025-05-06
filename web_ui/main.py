from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import asyncio
import logging
from typing import List, Dict, Any, Optional
import os
import sys

# Add parent directory to path so we can import OWLBEAR modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import OWLBEAR modules
from .models import (
    WorkflowListResponse,
    WorkflowDetailResponse,
    WorkflowExecuteRequest,
    ExpertListResponse,
    ExpertDetailResponse,
    ExecutionListResponse,
    ExecutionDetailResponse,
    StringsListResponse,
    WebSocketMessage
)
from .services.workflow_service import WorkflowService
from .services.expert_service import ExpertService
from .services.execution_service import ExecutionService
from .services.event_service import EventService
from .services.event_connector import EventConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("owlbear-web-ui")

# Initialize services
workflow_service = WorkflowService()
expert_service = ExpertService()
execution_service = ExecutionService()
event_service = EventService()
# Initialize event connector and connect to OWLBEAR events
event_connector = EventConnector(event_service)
event_connector.connect()

# Initialize FastAPI app
app = FastAPI(
    title="OWLBEAR Web UI",
    description="Web interface for the OWLBEAR multi-agent orchestration system",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes

@app.get("/api/workflows", response_model=WorkflowListResponse, tags=["Workflows"])
async def list_workflows():
    """
    List all available workflows in the system.
    """
    workflows = await workflow_service.list_workflows()
    return WorkflowListResponse(workflows=workflows)


@app.get("/api/strings", response_model=StringsListResponse, tags=["Strings"])
async def list_strings():
    """
    List all available strings files in the system.
    """
    strings_files = await workflow_service.list_strings_files()
    return StringsListResponse(strings_files=strings_files)


@app.get("/api/workflows/{workflow_id}", response_model=WorkflowDetailResponse, tags=["Workflows"])
async def get_workflow_details(workflow_id: str):
    """
    Get detailed information about a specific workflow.
    """
    try:
        workflow = await workflow_service.get_workflow_details(workflow_id)
        return WorkflowDetailResponse(**workflow)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


@app.post("/api/workflows/{workflow_id}/execute", tags=["Workflows"])
async def execute_workflow(workflow_id: str, request: WorkflowExecuteRequest):
    """
    Execute a workflow with the provided parameters.
    """
    try:
        execution_id = await workflow_service.execute_workflow(workflow_id, request.parameters)
         # Register the execution with the event connector
        event_connector.register_execution(workflow_id, execution_id)

        return {"execution_id": execution_id, "status": "started"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/workflows/{workflow_id}/cancel", tags=["Workflows"])
async def cancel_workflow(workflow_id: str, execution_id: str = Query(...)):
    """
    Cancel a running workflow execution.
    """
    try:
        success = await workflow_service.cancel_workflow(workflow_id, execution_id)
        if success:
            return {"status": "cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel workflow")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/experts", response_model=ExpertListResponse, tags=["Experts"])
async def list_experts():
    """
    List all available experts in the system.
    """
    experts = await expert_service.list_experts()
    return ExpertListResponse(experts=experts)


@app.get("/api/experts/{expert_id}", response_model=ExpertDetailResponse, tags=["Experts"])
async def get_expert_details(expert_id: str):
    """
    Get detailed information about a specific expert.
    """
    try:
        expert = await expert_service.get_expert_details(expert_id)
        return ExpertDetailResponse(**expert)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Expert {expert_id} not found")


@app.get("/api/executions", response_model=ExecutionListResponse, tags=["Executions"])
async def list_executions():
    """
    List recent workflow executions.
    """
    executions = await execution_service.list_executions()
    return ExecutionListResponse(executions=executions)


@app.get("/api/executions/{execution_id}", response_model=ExecutionDetailResponse, tags=["Executions"])
async def get_execution_details(execution_id: str):
    """
    Get detailed information about a specific execution.
    """
    try:
        execution = await execution_service.get_execution_details(execution_id)
        return ExecutionDetailResponse(**execution)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")


@app.websocket("/ws/execution/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for real-time updates on workflow execution.
    """
    await websocket.accept()
    
    # Register client for this execution
    await event_service.register_client(execution_id, websocket)
    
    try:
        # Keep the connection open and send periodic health checks
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "health_check"})
    except WebSocketDisconnect:
        # Clean up when client disconnects
        await event_service.unregister_client(execution_id, websocket)


# Serve frontend
app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse("web_ui/static/index.html")

@app.get("/logo", include_in_schema=False)
async def get_logo():
    return FileResponse("web_ui/static/owlbear_logo_head.png")


@app.on_event("shutdown")
async def shutdown_event():
    # Disconnect event connector before shutting down
    event_connector.disconnect()
    logger.info("Shutting down OWLBEAR Web UI")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8069)
