# Transitioning from Demo to Production Library: KOI-MCP Integration

Based on the architectural overview, I see that the key value of this system isn't about "personalities" specifically, but rather the powerful pattern it demonstrates for distributed knowledge representation, dissemination, and discovery. Let me outline what a production-ready, extensible library version of this integration would look like.

## Core Architecture for a Production Library

### 1. Modular, Domain-Agnostic Core

The production library should abstract away the "personality" specific elements and provide a generic framework:

```python
# Example core module structure
koi_mcp/
  ├── core/
  │   ├── rid/
  │   │   ├── base.py         # Base RID extension framework
  │   │   └── registry.py     # RID type registry
  │   ├── schema/
  │   │   ├── base.py         # Base schema models
  │   │   └── registry.py     # Schema registry
  │   ├── adapter/
  │   │   ├── base.py         # Abstract adapter interface
  │   │   └── registry.py     # Adapter registry
  │   ├── handlers/
  │   │   ├── base.py         # Handler interfaces
  │   │   ├── rid.py          # Generic RID handlers
  │   │   ├── bundle.py       # Generic bundle handlers
  │   │   └── network.py      # Generic network handlers
  │   └── nodes/
  │       ├── base.py         # Base node classes
  │       ├── coordinator.py  # Coordinator node base
  │       └── producer.py     # Producer node base
  ├── adapters/              # Concrete adapter implementations
  ├── extensions/            # Domain-specific extensions
  ├── server/                # MCP server implementations
  ├── utils/                 # Utility functions
  └── config.py              # Configuration management
```

### 2. Domain Extension Framework

The library should provide a clear extension mechanism for new domain types:

```python
class DomainExtension:
    """Base class for domain-specific KOI-MCP extensions."""

    @property
    def rid_types(self):
        """Return RID types for this domain."""
        return []

    @property
    def schemas(self):
        """Return schemas for this domain."""
        return []

    @property
    def adapters(self):
        """Return MCP adapters for this domain."""
        return []

    def register_handlers(self, processor):
        """Register domain-specific handlers."""
        pass
```

### 3. Plugin Architecture

Implement a plugin system that allows easy registration of domain extensions:

```python
class KoiMcpRegistry:
    """Central registry for KOI-MCP extensions."""

    def __init__(self):
        self.extensions = {}
        self.rid_types = {}
        self.schemas = {}
        self.adapters = {}

    def register_extension(self, name, extension):
        """Register a domain extension."""
        self.extensions[name] = extension

        # Register RID types
        for rid_type in extension.rid_types:
            self.rid_types[rid_type.namespace] = rid_type

        # Register schemas
        for schema in extension.schemas:
            self.schemas[schema.__name__] = schema

        # Register adapters
        for adapter in extension.adapters:
            self.adapters[adapter.__name__] = adapter

    def configure_node(self, node, domain_names=None):
        """Configure a node with registered extensions."""
        domains = domain_names or self.extensions.keys()

        for name in domains:
            if name in self.extensions:
                extension = self.extensions[name]
                extension.register_handlers(node.processor)
```

### 4. Domain-Agnostic Coordinator and Producer Base Classes

Create base classes that can be customized for specific domains but handle the core networking and adapter coordination:

```python
class CoordinatorNode:
    """Base coordinator node that can host multiple domain adapters."""

    def __init__(self, name, base_url, registry_port, domains=None):
        self.registry = KoiMcpRegistry()

        # Initialize with domain extensions
        if domains:
            for domain in domains:
                self.registry.register_extension(domain.name, domain)

        # Initialize node with all registered RID types
        self.node = self._create_node(name, base_url)

        # Initialize adapters
        self.adapters = self._create_adapters()

        # Initialize server
        self.server = self._create_server(registry_port)

        # Configure node with extensions
        self.registry.configure_node(self.node)

    def _create_node(self, name, base_url):
        # Create node with all registered RID types
        pass

    def _create_adapters(self):
        # Create adapters from registry
        pass

    def _create_server(self, port):
        # Create server with all adapters
        pass
```

### 5. Extensible Schema System

Provide a robust base for schema definition and transformation:

```python
class SchemaRegistry:
    """Registry for domain schemas with validation and transformation."""

    def __init__(self):
        self.schemas = {}
        self.transformers = {}

    def register_schema(self, schema_cls):
        """Register a schema class."""
        self.schemas[schema_cls.__name__] = schema_cls

    def register_transformer(self, source_schema, target_schema, transformer):
        """Register a transformer between schemas."""
        key = (source_schema.__name__, target_schema.__name__)
        self.transformers[key] = transformer

    def transform(self, source_obj, target_schema_name):
        """Transform an object from one schema to another."""
        source_name = source_obj.__class__.__name__
        key = (source_name, target_schema_name)

        if key in self.transformers:
            return self.transformers[key](source_obj)

        raise ValueError(f"No transformer found for {source_name} to {target_schema_name}")
```

## Key Production Features

### 1. Robust Error Handling and Recovery

```python
class RobustKnowledgeHandler:
    """Base class for handlers with retry and error recovery."""

    def __init__(self, max_retries=3, backoff_factor=1.5):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def handle_with_retry(self, processor, kobj):
        """Handle a knowledge object with retry logic."""
        retries = 0
        delay = 1.0

        while retries < self.max_retries:
            try:
                return await self.handle(processor, kobj)
            except TransientError as e:
                logger.warning(f"Transient error handling {kobj.rid}: {e}")
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to handle {kobj.rid} after {retries} retries")
                    return self.handle_failure(processor, kobj, e)

                await asyncio.sleep(delay)
                delay *= self.backoff_factor
            except PermanentError as e:
                logger.error(f"Permanent error handling {kobj.rid}: {e}")
                return self.handle_failure(processor, kobj, e)

    async def handle(self, processor, kobj):
        """Handle a knowledge object."""
        raise NotImplementedError

    def handle_failure(self, processor, kobj, error):
        """Handle a failure to process a knowledge object."""
        return STOP_CHAIN
```

### 2. Monitoring and Observability

```python
class ObservableAdapter:
    """Adapter with built-in monitoring."""

    def __init__(self, metrics_registry=None):
        self.metrics = metrics_registry or PrometheusMetrics()
        self.register_counter = self.metrics.create_counter(
            "adapter_registrations_total",
            "Total number of registrations processed by adapter"
        )
        self.query_counter = self.metrics.create_counter(
            "adapter_queries_total",
            "Total number of queries processed by adapter"
        )
        self.error_counter = self.metrics.create_counter(
            "adapter_errors_total",
            "Total number of errors encountered by adapter"
        )

    def register_with_metrics(self, entity):
        """Register an entity with metrics collection."""
        try:
            self.register(entity)
            self.register_counter.inc({"entity_type": entity.__class__.__name__})
        except Exception as e:
            self.error_counter.inc({"operation": "register", "error": str(e)})
            raise
```

### 3. Authentication and Authorization

```python
class SecureCoordinatorNode(CoordinatorNode):
    """Coordinator with authentication and authorization."""

    def __init__(self, name, base_url, registry_port, auth_config, **kwargs):
        super().__init__(name, base_url, registry_port, **kwargs)
        self.auth_manager = AuthManager(auth_config)

    def _create_server(self, port):
        server = super()._create_server(port)

        # Add authentication middleware
        server.app.middleware("http")(self.auth_middleware)

        # Add authorization handlers
        for route in server.app.routes:
            route.endpoint = self.authorize(route.endpoint)

        return server

    async def auth_middleware(self, request, call_next):
        """Authenticate incoming requests."""
        token = request.headers.get("Authorization")
        if not token:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        try:
            request.state.user = self.auth_manager.validate_token(token)
            return await call_next(request)
        except AuthError as e:
            return JSONResponse(status_code=401, content={"error": str(e)})

    def authorize(self, endpoint):
        """Wrap endpoint with authorization check."""
        async def authorized_endpoint(*args, **kwargs):
            request = kwargs.get("request")
            if not request or not hasattr(request.state, "user"):
                return JSONResponse(status_code=401, content={"error": "Unauthorized"})

            # Check permissions
            required_permissions = getattr(endpoint, "required_permissions", [])
            if required_permissions:
                user_permissions = request.state.user.permissions
                if not all(perm in user_permissions for perm in required_permissions):
                    return JSONResponse(status_code=403, content={"error": "Forbidden"})

            return await endpoint(*args, **kwargs)

        return authorized_endpoint
```

### 4. Persistence and Recovery

```python
class PersistentCoordinatorNode(CoordinatorNode):
    """Coordinator with persistence and recovery capabilities."""

    def __init__(self, name, base_url, registry_port, storage_config, **kwargs):
        self.storage = StorageProvider.create(storage_config)
        super().__init__(name, base_url, registry_port, **kwargs)

    async def start(self):
        """Start the node with recovery."""
        await super().start()

        # Recover state from persistent storage
        await self.recover_state()

    async def recover_state(self):
        """Recover state from persistent storage."""
        # Load registered entities
        entities = await self.storage.load_all()

        # Re-register entities with adapters
        for entity in entities:
            for adapter in self.adapters.values():
                if adapter.can_handle(entity):
                    await adapter.register(entity)

    async def handle_bundle(self, processor, kobj):
        """Handle a bundle and persist it."""
        result = await super().handle_bundle(processor, kobj)

        # Persist the bundle if processing succeeded
        if result != STOP_CHAIN:
            await self.storage.store(kobj.rid, kobj.contents)

        return result
```

## Domain-Specific Extensions

Instead of hard-coding "personalities," the library would provide example extensions:

```python
# Example: Data Catalog Extension
class DataCatalogExtension(DomainExtension):
    """Extension for distributed data catalog functionality."""

    @property
    def name(self):
        return "data_catalog"

    @property
    def rid_types(self):
        return [DatasetRID, DataSchemaRID]

    @property
    def schemas(self):
        return [DatasetMetadata, DataSchemaDefinition]

    @property
    def adapters(self):
        return [DatasetAdapter]

    def register_handlers(self, processor):
        # Register dataset handlers
        @processor.register_handler(HandlerType.RID, rid_types=[DatasetRID])
        def dataset_rid_handler(proc, kobj):
            # Implementation
            return kobj

        # More handlers...

# Example: Service Registry Extension
class ServiceRegistryExtension(DomainExtension):
    """Extension for distributed service registry."""

    @property
    def name(self):
        return "service_registry"

    @property
    def rid_types(self):
        return [ServiceRID, EndpointRID]

    # More implementation...
```

## API Design

The public API would be clean and focused on the extension patterns:

```python
# Example usage
from koi_mcp import CoordinatorNode, ProducerNode, DomainExtension
from koi_mcp.extensions.data_catalog import DataCatalogExtension
from koi_mcp.extensions.service_registry import ServiceRegistryExtension

# Create a coordinator with multiple domains
coordinator = CoordinatorNode(
    name="multi-domain-coordinator",
    base_url="http://localhost:9000/koi-net",
    registry_port=9000,
    domains=[
        DataCatalogExtension(),
        ServiceRegistryExtension()
    ]
)

# Create a data producer
data_producer = ProducerNode(
    name="dataset-publisher",
    base_url="http://localhost:8100/koi-net",
    domains=[DataCatalogExtension()],
    first_contact="http://localhost:9000/koi-net"
)

# Publish a dataset
dataset_metadata = DatasetMetadata(
    name="customer_transactions",
    description="Daily customer transaction records",
    schema="transactions_schema_v1",
    format="parquet",
    location="s3://data-lake/transactions/",
    update_frequency="daily"
)

data_producer.publish(dataset_metadata)
```

## Configuration Management

Use a hierarchical, extensible configuration system:

```python
from pydantic import BaseSettings, Field
from typing import Dict, List, Optional, Any

class NetworkSettings(BaseSettings):
    first_contact: Optional[str] = None
    connect_timeout: float = 10.0
    request_timeout: float = 30.0
    max_retries: int = 3
    backoff_factor: float = 1.5

class PersistenceSettings(BaseSettings):
    storage_type: str = "file"  # or "redis", "postgres", etc.
    storage_path: str = ".koi/storage"
    ttl: Optional[int] = None

class SecuritySettings(BaseSettings):
    enable_auth: bool = False
    auth_provider: str = "none"  # or "jwt", "oauth", etc.
    auth_config: Dict[str, Any] = Field(default_factory=dict)

class DomainSettings(BaseSettings):
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)

class KoiMcpSettings(BaseSettings):
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    persistence: PersistenceSettings = Field(default_factory=PersistenceSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    domains: Dict[str, DomainSettings] = Field(default_factory=dict)

    class Config:
        env_prefix = "KOI_MCP_"
        env_nested_delimiter = "__"
```

## Deployment Considerations

The library should support various deployment scenarios:

1. **Embedded** - Library used within an existing application
2. **Standalone** - Run as a dedicated service
3. **Containerized** - Packaged with Docker for orchestration
4. **Serverless** - Adaptable to serverless environments

```python
# Example Docker-ready entrypoint
def entrypoint():
    """Container entrypoint for KOI-MCP services."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["coordinator", "producer", "consumer"])
    parser.add_argument("--config", default="/etc/koi-mcp/config.json")
    args = parser.parse_args()

    # Load config
    config = KoiMcpSettings.parse_file(args.config)

    # Set up logging
    setup_logging(config)

    # Initialize appropriate node type
    if args.role == "coordinator":
        node = create_coordinator_from_config(config)
    elif args.role == "producer":
        node = create_producer_from_config(config)
    elif args.role == "consumer":
        node = create_consumer_from_config(config)
    else:
        raise ValueError(f"Unknown role: {args.role}")

    # Start node
    node.start()

    # Set up signal handlers
    setup_signal_handlers(node)

    # Run until terminated
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.shutdown()
```

## Summary: From Demo to Production Library

The transition from the demo to a production library requires:

1. **Abstraction**: Replace the personality-specific code with a domain-agnostic core
2. **Extension**: Create a robust extension framework for domain-specific behaviors
3. **Resilience**: Add error handling, retry logic, and proper recovery mechanisms
4. **Observability**: Incorporate logging, metrics, and monitoring
5. **Security**: Add authentication, authorization, and secure communication
6. **Configurability**: Develop a comprehensive configuration system
7. **Deployment**: Support various deployment scenarios

The core architectural pattern remains the same:

- Define domain-specific RID types and schemas
- Distribute knowledge through the KOI network
- Transform to MCP-compatible resources via adapters
- Expose through standardized API endpoints

But the production library would be much more flexible, robust, and security-focused, with clear extension points for adding new domains beyond the personality example used in the demo.
