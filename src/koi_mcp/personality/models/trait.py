from typing import Any, Optional
from pydantic import BaseModel, Field

class PersonalityTrait(BaseModel):
    """Model representing a single personality trait."""
    name: str
    description: str = ""
    type: str
    value: Any
    is_callable: bool = False
    
    @classmethod
    def from_value(cls, name: str, value: Any, description: str = "", is_callable: bool = False):
        """Create a trait from a value."""
        return cls(
            name=name,
            description=description or f"{name} trait",
            type=type(value).__name__,
            value=value,
            is_callable=is_callable
        )
