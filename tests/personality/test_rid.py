import pytest
from koi_mcp.personality.rid import AgentPersonality

def test_agent_personality_rid():
    """Test AgentPersonality RID."""
    # Test constructor
    rid = AgentPersonality("test-agent", "1.0")
    assert rid.name == "test-agent"
    assert rid.version == "1.0"
    
    # Test reference property
    assert rid.reference == "test-agent/1.0"
    
    # Test from_reference
    rid2 = AgentPersonality.from_reference("test-agent/1.0")
    assert rid2.name == "test-agent"
    assert rid2.version == "1.0"
    
    # Test string representation
    assert str(rid) == "orn:agent.personality:test-agent/1.0"
    
    # Test equality
    assert rid == rid2
    
    # Test invalid reference
    with pytest.raises(ValueError):
        AgentPersonality.from_reference("invalid")
