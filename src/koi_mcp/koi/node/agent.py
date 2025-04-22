import logging
from typing import Dict, Any, Optional
from rid_lib.ext.bundle import Bundle
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.protocol.event import EventType, Event
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.profile import PersonalityProfile
from koi_mcp.personality.models.trait import PersonalityTrait
from koi_mcp.server.agent.agent_server import AgentPersonalityServer

logger = logging.getLogger(__name__)

class KoiAgentNode:
    """KOI node with agent personality capabilities."""
    
    def __init__(self, 
                 name: str,
                 version: str,
                 traits: Dict[str, Any],
                 base_url: str,
                 mcp_port: int,
                 first_contact: Optional[str] = None):
        
        # Create personality RID
        self.personality_rid = AgentPersonality(name, version)
        
        # Convert traits dict to PersonalityTraits
        self.traits = []
        for key, value in traits.items():
            # Check if value is a dict with trait metadata
            if isinstance(value, dict) and "description" in value:
                trait = PersonalityTrait(
                    name=key,
                    description=value.get("description", f"{key} trait for {name}"),
                    type=value.get("type", "object"),
                    value=value.get("value", None),
                    is_callable=value.get("is_callable", False)
                )
            else:
                trait = PersonalityTrait.from_value(
                    name=key,
                    value=value,
                    description=f"{key} trait for {name}"
                )
            self.traits.append(trait)
        
        # Initialize KOI node
        self.node = NodeInterface(
            name=name,
            profile=NodeProfile(
                base_url=base_url,
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[AgentPersonality],
                    state=[AgentPersonality]
                )
            ),
            use_kobj_processor_thread=True,
            first_contact=first_contact
        )
        
        # Create personality profile
        self.profile = PersonalityProfile(
            rid=self.personality_rid,
            node_rid=self.node.identity.rid,
            base_url=base_url,
            mcp_url=f"{base_url.rstrip('/')}/mcp",
            traits=self.traits
        )
        
        # Initialize MCP server
        self.mcp_server = AgentPersonalityServer(
            port=mcp_port,
            personality=self.profile
        )
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self):
        """Register knowledge handlers for the agent node."""
        from koi_mcp.koi.handlers.personality_handlers import (
            register_personality_handlers
        )
        register_personality_handlers(self.node.processor)
        
    def update_traits(self, traits: Dict[str, Any]):
        """Update agent's traits and broadcast changes."""
        # Update traits
        for key, value in traits.items():
            if self.profile.update_trait(key, value):
                logger.info(f"Updated trait '{key}' to '{value}'")
            else:
                # Create new trait
                trait = PersonalityTrait.from_value(
                    name=key,
                    value=value,
                    description=f"{key} trait for {self.profile.rid.name}"
                )
                self.profile.add_trait(trait)
                logger.info(f"Added new trait '{key}' with value '{value}'")
                
        # Create updated bundle
        bundle = Bundle.generate(
            rid=self.personality_rid,
            contents=self.profile.model_dump()
        )
        
        # Process bundle internally to broadcast to network
        self.node.processor.handle(bundle=bundle, event_type=EventType.UPDATE)
        logger.info(f"Broadcast personality update for {self.personality_rid}")
        
    def start(self):
        """Start the agent node."""
        logger.info(f"Starting agent node {self.node.identity.rid}")
        self.node.start()
        
        # Broadcast initial personality directly to the coordinator's broadcast endpoint
        bundle = Bundle.generate(
            rid=self.personality_rid,
            contents=self.profile.model_dump()
        )
        
        # Create a dedicated personality event
        personality_event = Event.from_bundle(EventType.NEW, bundle)
        
        # Find the coordinator in the first contact
        first_contact_url = self.node.network.first_contact
        if first_contact_url:
            logger.info(f"Broadcasting personality directly to coordinator: {first_contact_url}")
            try:
                # Directly use the request handler to send just the personality event
                self.node.network.request_handler.broadcast_events(
                    url=first_contact_url,
                    events=[personality_event]  # Only send the personality event
                )
                logger.info(f"Successfully sent personality to coordinator")
            except Exception as e:
                logger.error(f"Failed to broadcast personality: {e}")
        
        # Also process locally to ensure it's in our cache
        self.node.processor.handle(bundle=bundle, event_type=EventType.NEW)
        
        logger.info(f"Agent node started successfully")

