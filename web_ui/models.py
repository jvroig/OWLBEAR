from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime


class Expert(BaseModel):
    """Expert information model"""
    id: str = Field(..., description="Unique identifier for the expert (matches ExpertID in YAML)")
    name: str = Field(..., description="Display name for the expert")
    description: str = Field(..., description="Short description of the expert's role")
    tools: List[str] = Field(default=[], description="List of tools available to this expert")


class ExpertDetail(Expert):
    """Detailed expert information model"""
    system_prompt: str = Field(..., description="The system prompt used for this expert")
    endpoint: Optional[Dict[str, Any]] = Field(None, description="Endpoint configuration for this expert")


class WorkflowSummary(BaseModel):
    """Summary information about a workflow"""
    id: str = Field(..., description="Unique identifier for the workflow (filename without extension)")
    name: str = Field(..., description="Display name for the workflow")
    description: Optional[str] = Field(None, description="Short description of the workflow")
    expert_count: int = Field(..., description="Number of experts used in this workflow")
    action_count: int = Field(..., description="Number of actions in this workflow")


class WorkflowParameter(BaseModel):
    """Parameter required for workflow execution"""
    name: str = Field(..., description="Name of the parameter")
    description: Optional[str] = Field(None, description="Description of the parameter")
    required: bool = Field(default=True, description="Whether this parameter is required")
    default_value: Optional[str] = Field(None, description="Default value for the parameter")


class WorkflowDetail(WorkflowSummary):
    """Detailed information about a workflow"""
    experts: List[Expert] = Field(..., description="List of experts used in this workflow")
    parameters: List[WorkflowParameter] = Field(default=[], description="Parameters required for execution")
    has_tools: bool = Field(default=False, description="Whether this workflow uses any tools")
    has_decision_points: bool = Field(default=False, description="Whether this workflow has any DECIDE actions")


class ExecutionStatus(str, Enum):
    """Status of a workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionSummary(BaseModel):
    """Summary information about a workflow execution"""
    id: str = Field(..., description="Unique identifier for this execution")
    workflow_id: str = Field(..., description="ID of the workflow being executed")
    status: ExecutionStatus = Field(..., description="Current status of the execution")
    started_at: datetime = Field(..., description="When the execution started")
    completed_at: Optional[datetime] = Field(None, description="When the execution completed (if done)")
    current_step: Optional[int] = Field(None, description="Current step index (0-based)")
    error: Optional[str] = Field(None, description="Error message if execution failed")


class ExecutionStep(BaseModel):
    """Information about a step in a workflow execution"""
    step_index: int = Field(..., description="Index of this step in the workflow (0-based)")
    action_type: str = Field(..., description="Type of action (PROMPT, DECIDE, etc.)")
    expert_id: str = Field(..., description="ID of the expert performing this action")
    inputs: List[str] = Field(..., description="Inputs provided to this action")
    output_name: str = Field(..., description="Name of the output variable")
    timestamp: datetime = Field(..., description="When this step was executed")
    status: str = Field(..., description="Status of this step (completed, running, pending)")
    result: Optional[Any] = Field(None, description="Result of this step (if completed)")


class ToolCall(BaseModel):
    """Information about a tool call made by an expert"""
    expert_id: str = Field(..., description="ID of the expert making the tool call")
    tool_name: str = Field(..., description="Name of the tool being called")
    parameters: Dict[str, Any] = Field(..., description="Parameters passed to the tool")
    result: Optional[str] = Field(None, description="Result returned by the tool")
    timestamp: datetime = Field(..., description="When this tool call was made")


class ExecutionDetail(ExecutionSummary):
    """Detailed information about a workflow execution"""
    parameters: Dict[str, Any] = Field(default={}, description="Parameters provided for this execution")
    steps: List[ExecutionStep] = Field(default=[], description="Steps in this execution")
    tool_calls: List[ToolCall] = Field(default=[], description="Tool calls made during this execution")
    logs: List[str] = Field(default=[], description="Execution logs")


# Response models for API endpoints
class WorkflowListResponse(BaseModel):
    """Response model for listing workflows"""
    workflows: List[WorkflowSummary] = Field(..., description="List of available workflows")


class WorkflowDetailResponse(WorkflowDetail):
    """Response model for workflow details"""
    pass


class ExpertListResponse(BaseModel):
    """Response model for listing experts"""
    experts: List[Expert] = Field(..., description="List of available experts")


class ExpertDetailResponse(ExpertDetail):
    """Response model for expert details"""
    pass


class ExecutionListResponse(BaseModel):
    """Response model for listing executions"""
    executions: List[ExecutionSummary] = Field(..., description="List of workflow executions")


class ExecutionDetailResponse(ExecutionDetail):
    """Response model for execution details"""
    pass


class WorkflowExecuteRequest(BaseModel):
    """Request model for executing a workflow"""
    parameters: Dict[str, Any] = Field(default={}, description="Parameters for workflow execution")


# WebSocket message models
class MessageType(str, Enum):
    """Types of websocket messages"""
    LOG = "log"
    STEP_UPDATE = "step_update"
    TOOL_CALL = "tool_call"
    EXECUTION_STATUS = "execution_status"
    ERROR = "error"
    HEALTH_CHECK = "health_check"


class WebSocketMessage(BaseModel):
    """Base model for websocket messages"""
    type: MessageType = Field(..., description="Type of message")
    execution_id: str = Field(..., description="ID of the execution this message relates to")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this message was generated")
    data: Any = Field(..., description="Message data")
