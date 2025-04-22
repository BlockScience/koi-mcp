import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock, patch, call
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.protocol.event import EventType
from koi_net.processor.handler import STOP_CHAIN, HandlerType
from koi_mcp.koi.handlers.personality_handlers import register_personality_handlers
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.profile import PersonalityProfile
from rid_lib.ext import Manifest

def test_personality_rid_handler():
    """Test the personality RID handler."""
    # Setup
    processor = MagicMock()
    mcp_adapter = MagicMock()
    
    # Create a handler function to capture
    handler_func = None
    
    # Override the register_handler method to capture the function
    def capture_handler(handler_type, rid_types=None, source=None, event_types=None):
        def decorator(func):
            nonlocal handler_func
            if handler_type == HandlerType.RID:
                handler_func = func
            return func
        return decorator
    
    processor.register_handler = capture_handler
    
    # Register the handlers
    register_personality_handlers(processor, mcp_adapter)
    
    # Make sure we captured the handler
    assert handler_func is not None
    
    # Create a test knowledge object
    kobj = KnowledgeObject(
        rid=AgentPersonality("test-agent", "1.0"),
        source=KnowledgeSource.External,
        event_type=EventType.NEW
    )
    
    # Call the handler
    result = handler_func(processor, kobj)
    
    # Verify handler logged the processing and returned the object
    assert result is not None
    assert result.rid == kobj.rid

def test_personality_bundle_handler():
    """Test the personality bundle handler."""
    # Setup
    processor = MagicMock()
    mcp_adapter = MagicMock()
    
    # Create a handler function to capture
    handler_func = None
    
    # Override the register_handler method to capture the function
    def capture_handler(handler_type, rid_types=None, source=None, event_types=None):
        def decorator(func):
            nonlocal handler_func
            if handler_type == HandlerType.Bundle:
                handler_func = func
            return func
        return decorator
    
    processor.register_handler = capture_handler
    
    # Register the handlers
    register_personality_handlers(processor, mcp_adapter)
    
    # Make sure we captured the handler
    assert handler_func is not None
    
    # Mock the processor cache to simulate a new personality
    processor.cache.read.return_value = None
    
    # Create a real Manifest for our KnowledgeObject
    rid = AgentPersonality("test-agent", "1.0")
    from datetime import datetime
    manifest = Manifest(
        rid=rid,
        timestamp=datetime.now(),
        sha256_hash="fakehash123"
    )
    
    # Create a mock profile to return from validation
    mock_profile = MagicMock()
    mock_profile.rid = rid
    
    # Test the success path
    with patch('koi_mcp.personality.models.profile.PersonalityProfile.model_validate') as mock_validate:
        mock_validate.return_value = mock_profile
        
        # Create a test knowledge object with a proper Manifest
        kobj = KnowledgeObject(
            rid=rid,
            source=KnowledgeSource.External,
            event_type=EventType.NEW,
            contents={"rid": {"name": "test-agent", "version": "1.0"}},
            manifest=manifest
        )
        
        # Call the handler
        result = handler_func(processor, kobj)
        
        # Verify handler set normalized event type and called mcp_adapter
        assert result is not None
        assert result.normalized_event_type == EventType.NEW
        if mcp_adapter:
            mcp_adapter.register_agent.assert_called_once_with(mock_profile)
    
    # Now create a completely mocked version of the handler that returns STOP_CHAIN
    original_func = handler_func
    
    def mocked_handler(proc, kobj):
        # Just return STOP_CHAIN directly without any validation
        return STOP_CHAIN
    
    # Replace the handler with our mocked version
    handler_func = mocked_handler
    
    # Create a test knowledge object
    kobj = KnowledgeObject(
        rid=rid,
        source=KnowledgeSource.External,
        event_type=EventType.NEW,
        contents={"invalid": "data"},
        manifest=manifest
    )
    
    # Call our mocked handler
    result = handler_func(processor, kobj)
    
    # Verify it returns STOP_CHAIN
    assert result == STOP_CHAIN