import logging
from fastapi import FastAPI, HTTPException
from koi_mcp.server.adapter.mcp_adapter import MCPAdapter

logger = logging.getLogger(__name__)

class AgentRegistryServer:
    """MCP-compatible server that exposes agent registry."""
    
    def __init__(self, port: int, adapter: MCPAdapter, root_path: str = ""):
        self.port = port
        self.adapter = adapter
        self.app = FastAPI(
            title="KOI-MCP Agent Registry",
            description="MCP-compatible registry of agent personalities",
            version="0.1.0",
            root_path=root_path
        )
        
        # Set up routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.get("/resources/list")
        def list_resources():
            """List all available agent resources."""
            return {"resources": self.adapter.list_agents()}
                
        @self.app.get("/resources/read/{resource_id}")
        def read_resource(resource_id: str):
            """Read a specific agent resource."""
            if not resource_id.startswith("agent:"):
                raise HTTPException(status_code=404, detail="Resource not found")
                    
            agent_name = resource_id[6:]  # Strip "agent:" prefix
            agent = self.adapter.get_agent(agent_name)
                
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
                    
            return {
                "id": resource_id,
                "type": "agent_profile",
                "content": agent.model_dump()
            }
                
        @self.app.get("/tools/list")
        def list_tools():
            """List all available agent tools."""
            return {"tools": self.adapter.get_all_tools()}
