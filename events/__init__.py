"""
OWLBEAR Events Package.

This package provides event handling capabilities for the OWLBEAR framework.
"""
from .event_emitter import (
    emitter,
    EVENT_WORKFLOW_START,
    EVENT_WORKFLOW_END,
    EVENT_STEP_START,
    EVENT_STEP_END,
    EVENT_EXPERT_START,
    EVENT_EXPERT_END,
    EVENT_TOOL_CALL_START,
    EVENT_TOOL_CALL_END,
    EVENT_LOG,
    EVENT_ERROR
)
