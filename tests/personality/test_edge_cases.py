# personality/test_edge_cases.py

import pytest
from unittest.mock import MagicMock, patch
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.protocol.event import EventType
from koi_net.processor.handler import STOP_CHAIN  # Import STOP_CHAIN from the correct module
from koi_mcp.koi.handlers.personality_handlers import register_personality_handlers
from koi_mcp.personality.rid import AgentPersonality

def test_handler_with_invalid_contents():
    """Test handler behavior with invalid personality contents."""
    # Setup
    processor = MagicMock()
    mcp_adapter = MagicMock()
    register_personality_handlers(processor, mcp_adapter)
    
    # Extract the bundle handler function
    bundle_handler = processor.register_handler.call_args_list[1][1]['func']
    
    # Create a test knowledge object with invalid contents
    kobj = KnowledgeObject(
        rid=AgentPersonality("test-agent", "1.0"),
        source=KnowledgeSource.External,
        event_type=EventType.NEW,
        contents={"invalid": "content"},  # Invalid contents
        manifest=MagicMock()
    )
    
    # Call the handler
    result = bundle_handler(processor, kobj)
    
    # Verify handler returned STOP_CHAIN due to validation error
    assert result == STOP_CHAIN
    assert "Invalid personality profile format" in processor.logger.error.call_args_list[0][0][0]
    assert not mcp_adapter.register_agent.called

def test_own_personality_protection():
    """Test that a node protects its own personality from external updates."""
    # Setup
    processor = MagicMock()
    processor.personality_rid = AgentPersonality("my-agent", "1.0")
    mcp_adapter = MagicMock()
    register_personality_handlers(processor, mcp_adapter)
    
    # Extract the RID handler function
    rid_handler = processor.register_handler.call_args_list[0][1]['func']
    
    # Create a test knowledge object for the node's own personality from external source
    kobj = KnowledgeObject(
        rid=AgentPersonality("my-agent", "1.0"),  # Same as the node's personality
        source=KnowledgeSource.External,
        event_type=EventType.UPDATE
    )
    
    # Call the handler
    result = rid_handler(processor, kobj)
    
    # Verify handler returned STOP_CHAIN to protect its own personality
    assert result == STOP_CHAIN
    assert "Blocked external update to our personality" in processor.logger.warning.call_args_list[0][0][0]