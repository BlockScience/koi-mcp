# koi_mcp/koi/handlers/personality_handlers.py

import logging
from typing import Optional
from pydantic import ValidationError
from rid_lib.ext.bundle import Bundle
from koi_net.processor import ProcessorInterface
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.protocol.event import EventType, Event
from koi_net.protocol.helpers import generate_edge_bundle
from koi_net.protocol.edge import EdgeType
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.profile import PersonalityProfile

logger = logging.getLogger(__name__)

def register_personality_handlers(processor: ProcessorInterface, mcp_adapter=None):
    """Register all personality-related handlers with a processor."""
    
    @processor.register_handler(HandlerType.RID, rid_types=[AgentPersonality])
    def personality_rid_handler(proc: ProcessorInterface, kobj: KnowledgeObject):
        """Validate agent personality RIDs."""
        if hasattr(proc, "personality_rid") and kobj.rid == proc.personality_rid and kobj.source == KnowledgeSource.External:
            logger.warning(f"Blocked external update to our personality: {kobj.rid}")
            return STOP_CHAIN
        logger.info(f"Processing agent personality RID: {kobj.rid}")
        return kobj
    
    @processor.register_handler(HandlerType.Bundle, rid_types=[AgentPersonality])
    def personality_bundle_handler(proc: ProcessorInterface, kobj: KnowledgeObject):
        """Process agent personality bundles."""
        try:
            profile = PersonalityProfile.model_validate(kobj.contents)
            prev = proc.cache.read(kobj.rid)
            kobj.normalized_event_type = EventType.UPDATE if prev else EventType.NEW
            logger.info(f"{'Updating' if prev else 'Adding'} agent personality: {kobj.rid}")
            if mcp_adapter:
                mcp_adapter.register_agent(profile)
            return kobj
        except ValidationError as e:
            logger.error(f"Invalid personality profile for {kobj.rid}: {e}")
            return STOP_CHAIN

def generate_personality_edge(source_rid, target_rid):
    """Generate KOI-net edge bundle for AgentPersonality subscription."""
    return generate_edge_bundle(
        source=source_rid,
        target=target_rid,
        rid_types=[AgentPersonality],
        edge_type=EdgeType.POLL
    )