#!/usr/bin/env python3
"""
Test suite for cmem integration in memory server.
"""

import pytest
import asyncio
import json
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.memory.memory_server import MemoryServer


class TestCmemIntegration:
    """Test cmem integration functionality."""
    
    def setup_method(self):
        """Setup test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        
    def test_memory_server_initialization_default(self):
        """Test memory server initializes with default identity."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            assert server.current_project == "default"
            
    def test_memory_server_initialization_custom_identity(self):
        """Test memory server initializes with custom identity."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer(identity="test_project")
            assert server.current_project == "test_project"
            
    def test_setup_cmem_integration_no_cmem(self):
        """Test cmem integration setup when cmem is not available."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 1  # cmem not available
                
                server = MemoryServer()
                assert server.cmem_integration is False
                
    def test_setup_cmem_integration_available(self):
        """Test cmem integration setup when cmem is available."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0  # cmem available
                
                # Create mock .claude directory
                claude_dir = Path(self.temp_dir) / ".claude"
                claude_dir.mkdir()
                sessions_dir = claude_dir / "sessions" / "test_session"
                sessions_dir.mkdir(parents=True)
                
                server = MemoryServer()
                
                # Should have attempted cmem integration
                assert hasattr(server, 'cmem_integration')
                
    def test_create_cmem_bridges(self):
        """Test creation of cmem bridge files."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            
            identity_dir = Path(self.temp_dir) / ".mcp-memory" / "test"
            identity_dir.mkdir(parents=True)
            
            session_dir = Path(self.temp_dir) / "session"
            session_dir.mkdir()
            
            server._create_cmem_bridges(identity_dir, session_dir)
            
            bridge_dir = identity_dir / "cmem_bridge"
            assert bridge_dir.exists()
            
            info_file = bridge_dir / "info.json"
            assert info_file.exists()
            
            with open(info_file) as f:
                bridge_info = json.load(f)
            
            assert bridge_info["session_dir"] == str(session_dir)
            assert bridge_info["integration_active"] is True
            assert "last_sync" in bridge_info
            
    @pytest.mark.asyncio
    async def test_sync_task_to_cmem_add(self):
        """Test syncing task addition to cmem."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            from mcp_servers.memory.memory_server import Task
            task = Task(
                id="test-id",
                content="Test task",
                priority="high",
                assignee="test_user"
            )
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await server._sync_task_to_cmem(task, "add")
                
                # Verify subprocess was called with correct arguments
                mock_subprocess.assert_called_once()
                args = mock_subprocess.call_args[0]
                assert args[0] == "cmem"
                assert args[1] == "task"
                assert args[2] == "add"
                assert args[3] == "Test task"
                assert "--priority" in args
                assert "high" in args
                assert "--assignee" in args
                assert "test_user" in args
                
    @pytest.mark.asyncio
    async def test_sync_task_to_cmem_complete(self):
        """Test syncing task completion to cmem."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            from mcp_servers.memory.memory_server import Task
            task = Task(
                id="test-id",
                content="Test task completion",
                status="completed"
            )
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await server._sync_task_to_cmem(task, "complete")
                
                # Verify subprocess was called for completion
                mock_subprocess.assert_called_once()
                args = mock_subprocess.call_args[0]
                assert args[0] == "cmem"
                assert args[1] == "task"
                assert args[2] == "complete"
                assert "Test task completion"[:50] in args[3]  # Truncated content
                
    @pytest.mark.asyncio
    async def test_sync_pattern_to_cmem(self):
        """Test syncing pattern to cmem."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            from mcp_servers.memory.memory_server import Pattern
            pattern = Pattern(
                id="test-pattern-id",
                pattern="Test pattern",
                description="Pattern description",
                priority="high"
            )
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await server._sync_pattern_to_cmem(pattern, "add")
                
                # Verify subprocess was called with correct arguments
                mock_subprocess.assert_called_once()
                args = mock_subprocess.call_args[0]
                assert args[0] == "cmem"
                assert args[1] == "pattern"
                assert args[2] == "add"
                assert args[3] == "Test pattern"
                assert args[4] == "Pattern description"
                assert "--priority" in args
                assert "high" in args
                
    @pytest.mark.asyncio
    async def test_sync_decision_to_cmem(self):
        """Test syncing decision to cmem."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            from mcp_servers.memory.memory_server import Decision
            decision = Decision(
                id="test-decision-id",
                choice="Test choice",
                reasoning="Test reasoning",
                alternatives=["Alt 1", "Alt 2"]
            )
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await server._sync_decision_to_cmem(decision)
                
                # Verify subprocess was called with correct arguments
                mock_subprocess.assert_called_once()
                args = mock_subprocess.call_args[0]
                assert args[0] == "cmem"
                assert args[1] == "decision"
                assert args[2] == "Test choice"
                assert args[3] == "Test reasoning"
                assert args[4] == "Alt 1, Alt 2"
                
    @pytest.mark.asyncio
    async def test_sync_with_integration_disabled(self):
        """Test that sync methods do nothing when integration is disabled."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = False
            
            from mcp_servers.memory.memory_server import Task
            task = Task(id="test", content="test")
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                await server._sync_task_to_cmem(task, "add")
                
                # Should not have called subprocess
                mock_subprocess.assert_not_called()
                
    @pytest.mark.asyncio
    async def test_sync_error_handling(self):
        """Test that sync errors are handled gracefully."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            from mcp_servers.memory.memory_server import Task
            task = Task(id="test", content="test")
            
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_subprocess.side_effect = Exception("Subprocess error")
                
                # Should not raise exception
                await server._sync_task_to_cmem(task, "add")
                
    @pytest.mark.asyncio
    async def test_task_add_with_sync(self):
        """Test task addition triggers cmem sync."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            with patch.object(server, '_sync_task_to_cmem') as mock_sync:
                mock_sync.return_value = None  # Async function
                
                result = await server._task_add({
                    "content": "Test task",
                    "priority": "high"
                })
                
                # Verify sync was called
                mock_sync.assert_called_once()
                args = mock_sync.call_args[0]
                assert args[1] == "add"  # action
                assert args[0].content == "Test task"
                
                # Verify task was added
                assert "Added task:" in result["content"][0]["text"]
                
    @pytest.mark.asyncio
    async def test_task_update_completion_with_sync(self):
        """Test task completion triggers cmem sync."""
        with patch('pathlib.Path.home', return_value=Path(self.temp_dir)):
            server = MemoryServer()
            server.cmem_integration = True
            
            # Add a task first
            task_id = "test-task-id"
            server.tasks[task_id] = {
                "id": task_id,
                "content": "Test task",
                "status": "pending",
                "priority": "medium",
                "assignee": None,
                "created_at": "2025-01-01T00:00:00",
                "completed_at": None
            }
            
            with patch.object(server, '_sync_task_to_cmem') as mock_sync:
                mock_sync.return_value = None  # Async function
                
                result = await server._task_update({
                    "task_id": task_id,
                    "status": "completed"
                })
                
                # Verify sync was called
                mock_sync.assert_called_once()
                args = mock_sync.call_args[0]
                assert args[1] == "complete"  # action
                
                # Verify task was updated
                assert server.tasks[task_id]["status"] == "completed"
                assert server.tasks[task_id]["completed_at"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])