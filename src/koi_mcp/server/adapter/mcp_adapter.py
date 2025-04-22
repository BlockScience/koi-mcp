import logging
from typing import Dict, List, Optional
from koi_mcp.personality.models.profile import PersonalityProfile

logger = logging.getLogger(__name__)

class MCPAdapter:
    """Adapts KOI personalities to MCP resources and tools."""
    
    def __init__(self):
        self.agents: Dict[str, PersonalityProfile] = {}
        
    def register_agent(self, profile):
        # If we’ve already registered this agent, do nothing
        if profile.rid.name in self.agents:
            logger.debug(f"Agent {profile.rid.name} is already registered, skipping")
            return
        logger.info(f"Registering agent {profile.rid.name}")
        self.agents[profile.rid.name] = profile
        
    def get_agent(self, name: str) -> Optional[PersonalityProfile]:
        """Retrieve an agent profile by name."""
        return self.agents.get(name)
        
    def list_agents(self) -> List[Dict]:
        """Get list of all known agents as MCP resources."""
        return [
            {
                "id": f"agent:{agent.rid.name}",
                "type": "agent_profile",
                "description": f"Agent {agent.rid.name} personality profile",
                "url": agent.mcp_url
            }
            for agent in self.agents.values()
        ]
        
    def get_tools_for_agent(self, agent_name: str) -> List[Dict]:
        """Get list of tools provided by a specific agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            return []
            
        return [
            {
                "name": trait.name,
                "description": trait.description,
                "input_schema": {"type": "string"},
                "url": f"{agent.mcp_url}/tools/call/{trait.name}"
            }
            for trait in agent.traits
            if trait.is_callable
        ]
        
    def get_all_tools(self) -> List[Dict]:
        """Get list of all tools from all agents."""
        all_tools = []
        for agent_name in self.agents:
            tools = self.get_tools_for_agent(agent_name)
            for tool in tools:
                # Add agent name to tool name for uniqueness
                tool["name"] = f"{agent_name}.{tool['name']}"
                all_tools.append(tool)
        return all_tools
