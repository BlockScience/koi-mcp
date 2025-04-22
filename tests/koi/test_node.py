import pytest
from unittest.mock import MagicMock, patch
from koi_mcp.koi.node.agent import KoiAgentNode
from koi_mcp.koi.node.coordinator import CoordinatorAdapterNode
from koi_mcp.personality.rid import AgentPersonality
from rid_lib.types import KoiNetNode

def test_agent_node_init():
    """Test agent node initialization."""
    # Use the full import path
    with patch('koi_mcp.koi.node.agent.NodeInterface') as mock_node:
        # Set up the mock properly
        mock_instance = MagicMock()
        mock_node.return_value = mock_instance
        mock_instance.identity.rid = KoiNetNode.generate("test")
        
        agent = KoiAgentNode(
            name="test-agent",
            version="1.0",
            traits={"test": "value"},
            base_url="http://localhost:8000",
            mcp_port=8001
        )
        
        # Check that personality RID was created correctly
        assert agent.personality_rid.name == "test-agent"
        assert agent.personality_rid.version == "1.0"
        
        # Check that traits were converted correctly
        assert len(agent.traits) == 1
        assert agent.traits[0].name == "test"
        assert agent.traits[0].value == "value"
        
        # Check that KOI node was initialized
        assert mock_node.called

def test_coordinator_node_init():
    """Test coordinator node initialization."""
    # Use the full import path
    with patch('koi_mcp.koi.node.coordinator.NodeInterface') as mock_node:
        coordinator = CoordinatorAdapterNode(
            name="test-coordinator",
            base_url="http://localhost:8000",
            mcp_registry_port=9000
        )
        
        # Check that KOI node was initialized
        assert mock_node.called
        
        # Check that MCP adapter was initialized
        assert coordinator.mcp_adapter is not None
        
        # Check that registry server was initialized
        assert coordinator.registry_server is not None