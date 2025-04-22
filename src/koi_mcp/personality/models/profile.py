from typing import Any, List, Optional
from pydantic import BaseModel, Field
from rid_lib.types.koi_net_node import KoiNetNode
from koi_mcp.personality.rid import AgentPersonality
from koi_mcp.personality.models.trait import PersonalityTrait

class PersonalityProfile(BaseModel):
    """Model representing an agent's complete personality profile."""
    rid: AgentPersonality
    node_rid: KoiNetNode
    base_url: Optional[str] = None
    mcp_url: Optional[str] = None
    traits: List[PersonalityTrait] = Field(default_factory=list)
    
    def get_trait(self, name: str) -> Optional[PersonalityTrait]:
        """Get a trait by name."""
        for trait in self.traits:
            if trait.name == name:
                return trait
        return None
    
    def update_trait(self, name: str, value: Any) -> bool:
        """Update a trait's value."""
        for trait in self.traits:
            if trait.name == name:
                trait.value = value
                return True
        return False
    
    def add_trait(self, trait: PersonalityTrait) -> None:
        """Add a new trait."""
        self.traits.append(trait)
