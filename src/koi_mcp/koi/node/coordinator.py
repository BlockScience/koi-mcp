# Update file: koi_mcp/koi/node/coordinator.py

import logging
import uvicorn
from fastapi import FastAPI
from rid_lib.types import KoiNetNode, KoiNetEdge
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.processor.knowledge_object import KnowledgeSource
from koi_net.protocol.api_models import *
from koi_net.protocol.consts import *
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.profile import PersonalityProfile
from koi_mcp.server.adapter.mcp_adapter import MCPAdapter
from koi_mcp.server.registry.registry_server import AgentRegistryServer

logger = logging.getLogger(__name__)

class CoordinatorAdapterNode:
    """A specialized KOI node that integrates coordination functions with MCP adaptation."""
    
    def __init__(self, 
                 name: str, 
                 base_url: str,
                 mcp_registry_port: int = 9000):
        # Initialize KOI Coordinator Node
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
            use_kobj_processor_thread=True
        )
        
        # Initialize MCP Adapter with Registry
        self.mcp_adapter = MCPAdapter()
        
        # Register handlers
        self._register_handlers()
        
        # Initialize MCP Registry Server
        self.registry_server = AgentRegistryServer(
            port=mcp_registry_port,
            adapter=self.mcp_adapter,
            root_path="/koi-net"
        )
        
        # Add KOI-net protocol endpoints to the app
        self._add_koi_endpoints()
        
    def _register_handlers(self):
        """Register knowledge handlers for the coordinator node."""
        from koi_mcp.koi.handlers.personality_handlers import (
            register_personality_handlers
        )
        register_personality_handlers(self.node.processor, self.mcp_adapter)
    
    def _add_koi_endpoints(self):
        """Add KOI-net protocol endpoints to the FastAPI app."""
        app = self.registry_server.app
        
        # Add or modify the broadcast_events method in _add_koi_endpoints 
        @app.post(BROADCAST_EVENTS_PATH)
        def broadcast_events(req: EventsPayload):
            """Handle events broadcast from other nodes."""
            logger.info(f"Received {len(req.events)} events from broadcast")
            for event in req.events:
                # Log the incoming event in detail
                logger.info(f"Processing event: {event.event_type} {event.rid}")
                
                # Special handling for agent personalities
                if isinstance(event.rid, AgentPersonality):
                    logger.info(f"Received agent personality event: {event.rid}")
                    
                    # Create a bundle directly from the event
                    if event.manifest and event.contents:
                        bundle = Bundle(
                            manifest=event.manifest,
                            contents=event.contents
                        )
                        
                        # Register with MCP adapter if it exists
                        try:
                            # Validate as personality profile
                            profile = PersonalityProfile.model_validate(event.contents)
                            self.mcp_adapter.register_agent(profile)
                            logger.info(f"Successfully registered agent {profile.rid.name} with MCP adapter")
                            
                            # Cache the bundle
                            self.node.cache.write(bundle)
                            logger.info(f"Cached agent personality: {event.rid}")
                        except Exception as e:
                            logger.error(f"Failed to register personality: {e}")
                    else:
                        logger.warning(f"Agent personality event missing manifest or contents: {event.rid}")
                
                # Pass to normal processing pipeline
                self.node.processor.handle(event=event, source=KnowledgeSource.External)
            
            return {}
            
        @app.post(POLL_EVENTS_PATH)
        def poll_events(req: PollEvents) -> EventsPayload:
            """Handle event polling from other nodes."""
            events = self.node.network.flush_poll_queue(req.rid)
            return EventsPayload(events=events)
            
        @app.post(FETCH_RIDS_PATH)
        def fetch_rids(req: FetchRids) -> RidsPayload:
            """Handle RID fetching from other nodes."""
            return self.node.network.response_handler.fetch_rids(req)
            
        @app.post(FETCH_MANIFESTS_PATH)
        def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
            """Handle manifest fetching from other nodes."""
            return self.node.network.response_handler.fetch_manifests(req)
            
        @app.post(FETCH_BUNDLES_PATH)
        def fetch_bundles(req: FetchBundles) -> BundlesPayload:
            """Handle bundle fetching from other nodes."""
            return self.node.network.response_handler.fetch_bundles(req)
        
    def start(self):
        """Start the coordinator node."""
        logger.info(f"Starting coordinator node {self.node.identity.rid}")
        self.node.start()
        logger.info("Coordinator node started successfully")