# Update file: koi_mcp/koi/handlers/personality_handlers.py

import logging
from typing import Optional
from pydantic import ValidationError
from rid_lib.ext.bundle import Bundle
from koi_net.processor import ProcessorInterface
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.protocol.event import EventType, Event
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.profile import PersonalityProfile

logger = logging.getLogger(__name__)

def register_personality_handlers(processor: ProcessorInterface, mcp_adapter=None):
    """Register all personality-related handlers with a processor."""
    
    @processor.register_handler(HandlerType.RID, rid_types=[AgentPersonality])
    def personality_rid_handler(proc: ProcessorInterface, kobj: KnowledgeObject):
        """Validate agent personality RIDs."""
        # Only block external updates to our own personality (if we have one)
        if hasattr(proc, "personality_rid") and kobj.rid == proc.personality_rid and kobj.source == KnowledgeSource.External:
            logger.warning(f"Blocked external update to our personality: {kobj.rid}")
            return STOP_CHAIN
        
        # For all other personality RIDs, allow processing
        logger.info(f"Processing agent personality: {kobj.rid}")
        
        # Important: Make sure normalized event type is set for external personalities
        if kobj.source == KnowledgeSource.External and kobj.event_type in [EventType.NEW, EventType.UPDATE]:
            prev_bundle = proc.cache.read(kobj.rid)
            if prev_bundle:
                kobj.normalized_event_type = EventType.UPDATE
            else:
                kobj.normalized_event_type = EventType.NEW
        
        return kobj
    
    @processor.register_handler(HandlerType.Bundle, rid_types=[AgentPersonality])
    def personality_bundle_handler(proc: ProcessorInterface, kobj: KnowledgeObject):
        """Process agent personality bundles."""
        try:
            # Validate contents as PersonalityProfile
            profile = PersonalityProfile.model_validate(kobj.contents)
            
            # Set normalized event type based on cache status
            prev_bundle = proc.cache.read(kobj.rid)
            if prev_bundle:
                kobj.normalized_event_type = EventType.UPDATE
                logger.info(f"Updating existing agent personality: {kobj.rid}")
            else:
                kobj.normalized_event_type = EventType.NEW
                logger.info(f"Adding new agent personality: {kobj.rid}")
                
            # Register with MCP adapter if available
            if mcp_adapter is not None:
                mcp_adapter.register_agent(profile)
                logger.info(f"Registered agent {profile.rid.name} with MCP adapter")
                
            return kobj
            
        except ValidationError as e:
            logger.error(f"Invalid personality profile format: {kobj.rid} - {e}")
            return STOP_CHAIN
    
    @processor.register_handler(HandlerType.Network, rid_types=[AgentPersonality])
    def personality_network_handler(proc: ProcessorInterface, kobj: KnowledgeObject):
        """Determine which nodes to broadcast personality updates to."""
        # Get all neighbors interested in AgentPersonality
        subscribers = proc.network.graph.get_neighbors(
            direction="out",
            allowed_type=AgentPersonality
        )
        
        # Add all subscribers as network targets
        kobj.network_targets.update(subscribers)
        
        # If this is our personality, always broadcast
        if hasattr(proc, "personality_rid") and kobj.rid == proc.personality_rid:
            logger.debug("Broadcasting our own personality to all neighbors")
            kobj.network_targets.update(proc.network.graph.get_neighbors())
            
        return kobj