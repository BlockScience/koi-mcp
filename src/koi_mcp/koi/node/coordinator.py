import os
import logging
import uvicorn
from fastapi import FastAPI
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.processor.knowledge_object import KnowledgeSource
from koi_net.protocol.api_models import (
    EventsPayload, PollEvents, FetchRids, FetchManifests, FetchBundles,
    RidsPayload, ManifestsPayload, BundlesPayload
)
from koi_net.protocol.consts import (
    BROADCAST_EVENTS_PATH, POLL_EVENTS_PATH,
    FETCH_RIDS_PATH, FETCH_MANIFESTS_PATH, FETCH_BUNDLES_PATH
)
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.server.adapter.mcp_adapter import MCPAdapter
from koi_mcp.server.registry.registry_server import AgentRegistryServer
from koi_mcp.koi.handlers.personality_handlers import register_personality_handlers

logger = logging.getLogger(__name__)

class CoordinatorAdapterNode:
    """A specialized KOI node that integrates coordination functions with MCP adaptation."""
    
    def __init__(self, 
                 name: str, 
                 base_url: str,
                 mcp_registry_port: int = 9000):
        os.makedirs(f".koi/{name}", exist_ok=True)
        # 1. Build NodeInterface with built-in subscription to AgentPersonality
        self.node = NodeInterface(
            name=name,
            profile=NodeProfile(
                base_url=base_url,
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[KoiNetNode, KoiNetEdge, AgentPersonality],
                    state=[KoiNetNode, KoiNetEdge, AgentPersonality]
                )
            ),
            use_kobj_processor_thread=True,
            identity_file_path=f".koi/{name}/{name}_identity.json",
            event_queues_file_path=f".koi/{name}/{name}_event_queues.json",
            cache_directory_path=f".koi/{name}/rid_cache_{name}"
        )
        
        # 2. Install MCP adapter and kill manual broadcasts
        self.mcp_adapter = MCPAdapter()
        register_personality_handlers(self.node.processor, self.mcp_adapter)
        
        # 3. Spin up the MCP registry server
        self.registry_server = AgentRegistryServer(
            port=mcp_registry_port,
            adapter=self.mcp_adapter,
            root_path="/koi-net"
        )
        
        # 4. Wire KOI-net API endpoints
        self._add_koi_endpoints()
    
    def _add_koi_endpoints(self):
        app = self.registry_server.app
        
        @app.post(BROADCAST_EVENTS_PATH)
        def broadcast_events(req: EventsPayload):
            for event in req.events:
                self.node.processor.handle(event=event, source=KnowledgeSource.External)
            return {}
            
        @app.post(POLL_EVENTS_PATH)
        def poll_events(req: PollEvents) -> EventsPayload:
            return EventsPayload(events=self.node.network.flush_poll_queue(req.rid))
            
        @app.post(FETCH_RIDS_PATH)
        def fetch_rids(req: FetchRids) -> RidsPayload:
            return self.node.network.response_handler.fetch_rids(req)
            
        @app.post(FETCH_MANIFESTS_PATH)
        def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
            return self.node.network.response_handler.fetch_manifests(req)
            
        @app.post(FETCH_BUNDLES_PATH)
        def fetch_bundles(req: FetchBundles) -> BundlesPayload:
            return self.node.network.response_handler.fetch_bundles(req)
        
    def start(self):
        logger.info(f"Starting coordinator node {self.node.identity.rid}")
        self.node.start()
        logger.info("Coordinator node started successfully")