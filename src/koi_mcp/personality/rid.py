from rid_lib.core import ORN

class AgentPersonality(ORN):
    namespace = "agent.personality"
    
    def __init__(self, name, version):
        self.name = name
        self.version = version
        
    @property
    def reference(self):
        return f"{self.name}/{self.version}"
    
    @classmethod
    def from_reference(cls, reference):
        components = reference.split("/")
        if len(components) == 2:
            return cls(*components)
        else:
            raise ValueError(
                "Agent Personality reference must contain: '<name>/<version>'"
            )
