# src/koi_mcp/koi/node/agent.py
import os
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
from koi_mcp.koi.handlers.personality_handlers import (
    register_personality_handlers,
    generate_personality_edge,
)

logger = logging.getLogger(__name__)


class KoiAgentNode:
    """KOI node with agent personality capabilities."""

    def __init__(
        self,
        name: str,
        version: str,
        traits: Dict[str, Any],
        base_url: str,
        mcp_port: int,
        first_contact: Optional[str] = None,
    ):
        os.makedirs(f".koi/{name}", exist_ok=True)
        # 1. Convert raw traits dict into PersonalityTrait list
        self.traits: list[PersonalityTrait] = []
        for trait_name, trait_info in traits.items():
            if isinstance(trait_info, dict):
                description = trait_info.get("description", "")
                is_callable = trait_info.get("is_callable", False)
                trait_type = trait_info.get("type", "") or type(
                    trait_info.get("value", None)
                ).__name__
                value = trait_info.get("value", None)
            else:
                description = ""
                is_callable = False
                trait_type = type(trait_info).__name__
                value = trait_info

            self.traits.append(
                PersonalityTrait(
                    name=trait_name,
                    description=description,
                    type=trait_type,
                    value=value,
                    is_callable=is_callable,
                )
            )

        # 2. Create the AgentPersonality RID
        self.personality_rid = AgentPersonality(name, version)

        # 3. Instantiate KOI node, subscribing to AgentPersonality
        self.node = NodeInterface(
            name=name,
            profile=NodeProfile(
                base_url=base_url,
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[AgentPersonality],
                    state=[AgentPersonality],
                ),
            ),
            use_kobj_processor_thread=True,
            first_contact=first_contact,
            identity_file_path=f".koi/{name}/{name}_identity.json",
            event_queues_file_path=f".koi/{name}/{name}_event_queues.json",
            cache_directory_path=f".koi/{name}/rid_cache_{name}"
        )

        # 4. Build PersonalityProfile now that node_rid is available
        self.profile = PersonalityProfile(
            rid=self.personality_rid,
            node_rid=self.node.identity.rid,
            base_url=base_url,
            mcp_url=f"{base_url.rstrip('/')}/mcp",
            traits=self.traits,
        )

        # 5. Initialize MCP server for this agent
        self.mcp_server = AgentPersonalityServer(
            port=mcp_port,
            personality=self.profile,
        )

        # 6. Register personality handlers (and expose our RID for handler checks)
        register_personality_handlers(self.node.processor)
        setattr(self.node.processor, "personality_rid", self.personality_rid)

    # -------------------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------------------

    def start(self) -> None:
        """Start the agent node, publish personality, and connect to coordinator."""
        logger.info(f"Starting agent node {self.node.identity.rid}")
        self.node.start()

        # 1. Publish our personality bundle locally
        bundle = Bundle.generate(
            rid=self.personality_rid,
            contents=self.profile.model_dump(),
        )
        self.node.processor.handle(bundle=bundle, event_type=EventType.NEW)

        # 2. Immediately broadcast the personality bundle to first‑contact (coordinator)
        if self.node.network.first_contact:
            event = Event.from_bundle(EventType.NEW, bundle)
            try:
                self.node.network.request_handler.broadcast_events(
                    url=self.node.network.first_contact,
                    events=[event],
                )
                logger.debug("Broadcasted personality to coordinator")
            except Exception as exc:
                logger.warning(f"Failed to broadcast personality: {exc}")

        # 3. Discover coordinator RID and propose edge subscription
        if self.node.network.first_contact:
            resp = self.node.network.request_handler.poll_events(
                url=self.node.network.first_contact,
                rid=self.node.identity.rid,
            )
            coord_rid = next(
                (ev.rid for ev in resp.events if ev.rid != self.node.identity.rid), None
            )
            if coord_rid:
                edge_bundle = generate_personality_edge(
                    source_rid=self.node.identity.rid,
                    target_rid=coord_rid,
                )
                self.node.processor.handle(
                    bundle=edge_bundle, event_type=EventType.NEW
                )
                edge_event = Event.from_bundle(EventType.NEW, edge_bundle)
                self.node.network.request_handler.broadcast_events(
                    url=self.node.network.first_contact,
                    events=[edge_event],
                )

        logger.info("Agent node started successfully")