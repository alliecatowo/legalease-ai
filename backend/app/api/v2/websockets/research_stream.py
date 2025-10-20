"""
WebSocket endpoint for streaming research progress.

Provides real-time updates during research workflow execution, allowing
clients to monitor progress, receive finding notifications, and track
phase transitions without polling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from temporalio.client import Client

from app.infrastructure.workflows.temporal.client import get_temporal_client


logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Connection Manager ====================

class ConnectionManager:
    """
    Manages WebSocket connections for research progress streaming.

    Maintains a mapping of research_run_id to active WebSocket connections,
    handles connection lifecycle, and provides broadcast capabilities.
    """

    def __init__(self):
        """Initialize connection manager with empty connection pool."""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, research_run_id: str, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.

        Args:
            research_run_id: The research run ID to monitor
            websocket: WebSocket connection to register
        """
        await websocket.accept()

        async with self._lock:
            if research_run_id not in self.active_connections:
                self.active_connections[research_run_id] = set()
            self.active_connections[research_run_id].add(websocket)

        logger.info(
            f"WebSocket connected for research_run_id={research_run_id}. "
            f"Total connections: {len(self.active_connections[research_run_id])}"
        )

    async def disconnect(self, research_run_id: str, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            research_run_id: The research run ID
            websocket: WebSocket connection to unregister
        """
        async with self._lock:
            if research_run_id in self.active_connections:
                self.active_connections[research_run_id].discard(websocket)

                # Clean up empty sets
                if not self.active_connections[research_run_id]:
                    del self.active_connections[research_run_id]

        logger.info(f"WebSocket disconnected for research_run_id={research_run_id}")

    async def broadcast(self, research_run_id: str, message: dict):
        """
        Broadcast a message to all connections for a research run.

        Automatically removes dead connections during broadcast.

        Args:
            research_run_id: The research run ID
            message: JSON-serializable message to broadcast
        """
        if research_run_id not in self.active_connections:
            return

        dead_connections = set()

        for connection in self.active_connections[research_run_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Failed to send message to connection: {e}. "
                    "Marking for removal."
                )
                dead_connections.add(connection)

        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self.active_connections[research_run_id].discard(dead)

                # Clean up empty sets
                if not self.active_connections[research_run_id]:
                    del self.active_connections[research_run_id]

            logger.info(
                f"Removed {len(dead_connections)} dead connection(s) "
                f"for research_run_id={research_run_id}"
            )

    def get_connection_count(self, research_run_id: str) -> int:
        """
        Get number of active connections for a research run.

        Args:
            research_run_id: The research run ID

        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(research_run_id, set()))


# Global connection manager instance
manager = ConnectionManager()


# ==================== Helper Functions ====================

async def get_workflow_status(research_run_id: str, client: Client) -> Optional[dict]:
    """
    Query workflow status from Temporal.

    Args:
        research_run_id: The research run ID
        client: Temporal client

    Returns:
        Status dictionary or None if workflow not found
    """
    try:
        workflow_id = f"deep-research-{research_run_id}"
        handle = client.get_workflow_handle(workflow_id)

        # Verify workflow exists
        await handle.describe()

        # Query status
        status = await handle.query("get_status")
        return status

    except Exception as e:
        logger.error(f"Failed to get workflow status for {research_run_id}: {e}")
        return None


async def format_status_message(status: dict, message_type: str = "status") -> dict:
    """
    Format workflow status into WebSocket message.

    Args:
        status: Raw status dictionary from workflow
        message_type: Message type (status, progress, phase_change, etc.)

    Returns:
        Formatted message dictionary
    """
    return {
        "type": message_type,
        "data": {
            "phase": status.get("phase"),
            "progress_pct": status.get("progress_pct", 0.0),
            "current_activity": status.get("current_activity"),
            "findings_count": status.get("findings_count", 0),
            "citations_count": status.get("citations_count", 0),
            "is_paused": status.get("is_paused", False),
            "is_cancelled": status.get("is_cancelled", False),
            "error": status.get("error"),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== WebSocket Endpoint ====================

@router.websocket("/research/{research_run_id}/stream")
async def research_stream(
    websocket: WebSocket,
    research_run_id: str,
):
    """
    WebSocket endpoint for real-time research progress updates.

    Clients connect to this endpoint to receive live updates about:
    - Workflow phase transitions
    - Progress percentage changes
    - New findings discovered
    - Error notifications
    - Completion status

    Message Format:
        All messages follow this structure:
        {
            "type": "status" | "progress" | "phase_change" | "finding" | "completed" | "error",
            "data": {
                "phase": "DOCUMENT_ANALYSIS",
                "progress_pct": 45.0,
                "current_activity": "run_document_analysis",
                "findings_count": 23,
                "citations_count": 67,
                "is_paused": false,
                "is_cancelled": false,
                "error": null
            },
            "timestamp": "2024-01-15T10:30:00.123456"
        }

    Message Types:
        - status: Initial status when connecting
        - progress: Periodic progress updates (every 2 seconds)
        - phase_change: Workflow moved to a new phase
        - finding: New finding discovered (future enhancement)
        - completed: Workflow completed successfully
        - error: Workflow failed or encountered an error

    Connection Lifecycle:
        1. Client connects
        2. Server sends initial status message
        3. Server polls workflow every 2 seconds and sends updates
        4. When workflow completes/fails, server sends final message and closes
        5. Client can disconnect at any time

    Args:
        websocket: WebSocket connection
        research_run_id: The research run ID to monitor

    Example:
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/api/v2/research/research_abc123/stream');

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log(`${message.type}: ${message.data.phase} - ${message.data.progress_pct}%`);

            if (message.type === 'completed') {
                console.log('Research completed!');
                ws.close();
            }
        };
        ```
    """
    # Get Temporal client
    try:
        client = await get_temporal_client()
    except Exception as e:
        logger.error(f"Failed to get Temporal client: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # Connect and register WebSocket
    await manager.connect(research_run_id, websocket)

    try:
        # Send initial status
        initial_status = await get_workflow_status(research_run_id, client)

        if initial_status is None:
            # Workflow not found
            await websocket.send_json({
                "type": "error",
                "data": {
                    "error": f"Research run {research_run_id} not found"
                },
                "timestamp": datetime.utcnow().isoformat(),
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Send initial status message
        initial_message = await format_status_message(initial_status, "status")
        await websocket.send_json(initial_message)

        # Track last phase to detect changes
        last_phase = initial_status.get("phase")
        last_progress = initial_status.get("progress_pct", 0.0)

        # Poll for updates and stream to client
        poll_interval = 2.0  # seconds
        max_poll_count = 7200  # 4 hours max (2s * 7200 = 14400s = 4h)
        poll_count = 0

        while poll_count < max_poll_count:
            poll_count += 1

            # Wait before next poll
            await asyncio.sleep(poll_interval)

            # Get latest status from Temporal
            current_status = await get_workflow_status(research_run_id, client)

            if current_status is None:
                # Workflow disappeared or error
                await websocket.send_json({
                    "type": "error",
                    "data": {
                        "error": "Lost connection to workflow"
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                })
                break

            current_phase = current_status.get("phase")
            current_progress = current_status.get("progress_pct", 0.0)

            # Detect phase change
            if current_phase != last_phase:
                await websocket.send_json(
                    await format_status_message(current_status, "phase_change")
                )
                last_phase = current_phase
                logger.info(
                    f"Phase change for {research_run_id}: {current_phase} "
                    f"({current_progress}%)"
                )

            # Send progress update (only if progress changed significantly)
            elif abs(current_progress - last_progress) >= 1.0:
                await websocket.send_json(
                    await format_status_message(current_status, "progress")
                )
                last_progress = current_progress

            # Check if workflow completed or failed
            if current_phase in ["COMPLETED", "FAILED", "CANCELLED"]:
                message_type = "completed" if current_phase == "COMPLETED" else "error"

                await websocket.send_json(
                    await format_status_message(current_status, message_type)
                )

                logger.info(
                    f"Workflow {research_run_id} reached terminal state: {current_phase}"
                )

                # Close connection after terminal state
                await asyncio.sleep(1)  # Give client time to process
                break

            # Handle paused state - send update less frequently
            if current_status.get("is_paused"):
                await asyncio.sleep(5)  # Poll every 7 seconds when paused

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from research_run_id={research_run_id}")

    except Exception as e:
        logger.error(
            f"WebSocket error for research_run_id={research_run_id}: {e}",
            exc_info=True
        )
        try:
            await websocket.send_json({
                "type": "error",
                "data": {
                    "error": f"Internal server error: {str(e)}"
                },
                "timestamp": datetime.utcnow().isoformat(),
            })
        except:
            pass  # Connection may already be closed

    finally:
        # Always disconnect and clean up
        await manager.disconnect(research_run_id, websocket)
        try:
            await websocket.close()
        except:
            pass  # Connection may already be closed


# ==================== Broadcast Functions ====================
# These can be called from other parts of the application to push updates

async def broadcast_finding(research_run_id: str, finding: dict):
    """
    Broadcast a new finding to all connected clients.

    Args:
        research_run_id: The research run ID
        finding: Finding dictionary to broadcast

    Example:
        >>> await broadcast_finding("research_abc123", {
        ...     "id": "finding_xyz",
        ...     "type": "FACT",
        ...     "text": "...",
        ... })
    """
    await manager.broadcast(research_run_id, {
        "type": "finding",
        "data": finding,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_error(research_run_id: str, error: str):
    """
    Broadcast an error to all connected clients.

    Args:
        research_run_id: The research run ID
        error: Error message
    """
    await manager.broadcast(research_run_id, {
        "type": "error",
        "data": {"error": error},
        "timestamp": datetime.utcnow().isoformat(),
    })
