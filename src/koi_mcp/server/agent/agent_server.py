import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from koi_mcp.personality.models.profile import PersonalityProfile

logger = logging.getLogger(__name__)

class AgentPersonalityServer:
    """MCP-compatible server for a single agent's personality."""
    
    def __init__(self, port: int, personality: PersonalityProfile):
        self.port = port
        self.personality = personality
        self.app = FastAPI(
            title=f"{personality.rid.name} MCP Server",
            description=f"MCP-compatible server for {personality.rid.name} agent",
            version="0.1.0"
        )
        
        # Set up routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.get("/resources/list")
        def list_resources():
            """List agent personality as a resource."""
            return {
                "resources": [
                    {
                        "id": f"agent:{self.personality.rid.name}",
                        "type": "agent_profile",
                        "description": f"{self.personality.rid.name} agent personality",
                        "url": f"/resources/read/agent:{self.personality.rid.name}"
                    }
                ]
            }
                
        @self.app.get("/resources/read/agent:{agent_name}")
        def read_resource(agent_name: str):
            """Read agent personality resource."""
            if agent_name != self.personality.rid.name:
                raise HTTPException(status_code=404, detail="Agent not found")
                    
            return {
                "id": f"agent:{agent_name}",
                "type": "agent_profile",
                "content": self.personality.model_dump()
            }
                
        @self.app.get("/tools/list")
        def list_tools():
            """List all callable traits as tools."""
            tools = [
                {
                    "name": trait.name,
                    "description": trait.description,
                    "input_schema": {"type": "string"},
                    "url": f"/tools/call/{trait.name}"
                }
                for trait in self.personality.traits
                if trait.is_callable
            ]
            return {"tools": tools}
            
        @self.app.post("/tools/call/{trait_name}")
        def call_tool(trait_name: str, input: Dict[str, Any] = {}):
            """Call a trait as a tool."""
            trait = self.personality.get_trait(trait_name)
            
            if not trait:
                raise HTTPException(status_code=404, detail=f"Trait {trait_name} not found")
                
            if not trait.is_callable:
                raise HTTPException(status_code=400, detail=f"Trait {trait_name} is not callable")
                
            # Return the trait value for this simple demo
            # In a real implementation, this would call a function
            return {
                "result": f"Value of {trait_name}: {trait.value}"
            }
