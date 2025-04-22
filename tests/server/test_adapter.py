import pytest
from koi_mcp.server.adapter.mcp_adapter import MCPAdapter
from koi_mcp.personality.models.profile import PersonalityProfile
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.trait import PersonalityTrait
from rid_lib.types import KoiNetNode

def test_mcp_adapter():
    """Test MCPAdapter."""
    adapter = MCPAdapter()
    
    # Create a test profile with a proper KoiNetNode RID
    node_rid = KoiNetNode.generate("test-node")
    
    profile = PersonalityProfile(
        rid=AgentPersonality("test-agent", "1.0"),
        node_rid=node_rid,  # Use a valid RID object
        base_url="http://localhost:8000",
        mcp_url="http://localhost:8001",
        traits=[
            PersonalityTrait(
                name="test",
                description="Test trait",
                type="string",
                value="value",
                is_callable=True
            )
        ]
    )
    
    # Register agent
    adapter.register_agent(profile)
    
    # Test get_agent
    assert adapter.get_agent("test-agent") == profile
    assert adapter.get_agent("nonexistent") is None
    
    # Test list_agents
    agents = adapter.list_agents()
    assert len(agents) == 1
    assert agents[0]["id"] == "agent:test-agent"
    
    # Test get_tools_for_agent
    tools = adapter.get_tools_for_agent("test-agent")
    assert len(tools) == 1
    assert tools[0]["name"] == "test"
    
    # Test get_all_tools
    all_tools = adapter.get_all_tools()
    assert len(all_tools) == 1
    assert all_tools[0]["name"] == "test-agent.test"