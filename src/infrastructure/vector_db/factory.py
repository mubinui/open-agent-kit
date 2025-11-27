"""Factory for creating vector database clients."""

import logging
from typing import Any, Optional

from src.config.vector_db_models import VectorDBConfig, VectorDBType
from src.infrastructure.vector_db.base import VectorDBClient
from src.infrastructure.vector_db.chromadb_client import ChromaDBClient
from src.infrastructure.vector_db.pgvector_client import PGVectorClient
from src.infrastructure.vector_db.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# Global provider adapter reference (set by application initialization)
_provider_adapter: Optional["ProviderAdapter"] = None


def set_provider_adapter(adapter: "ProviderAdapter") -> None:
    """
    Set the global provider adapter for the factory.
    
    Args:
        adapter: Provider adapter instance
    """
    global _provider_adapter
    _provider_adapter = adapter
    logger.info("VectorDBFactory configured with ProviderAdapter")


class VectorDBFactory:
    """Factory for creating vector database clients based on configuration."""

    @staticmethod
    def create_client(config: VectorDBConfig) -> VectorDBClient:
        """Create a vector database client based on configuration.
        
        This method will use the ProviderAdapter if available, otherwise
        falls back to direct client creation.
        
        Args:
            config: Vector database configuration
            
        Returns:
            VectorDBClient instance
            
        Raises:
            ValueError: If database type is not supported
        """
        # Try to use provider adapter if available
        if _provider_adapter is not None:
            try:
                logger.info(
                    f"Using ProviderAdapter to create vector DB client for '{config.collection_name}'"
                )
                return _provider_adapter.get_vector_db_client(config.collection_name)
            except Exception as e:
                logger.warning(
                    f"Failed to use ProviderAdapter, falling back to direct creation: {e}"
                )
        
        # Fallback to direct client creation
        # Validate configuration
        config.validate_config()
        
        if config.type == VectorDBType.CHROMADB:
            logger.info(f"Creating ChromaDB client for collection '{config.collection_name}'")
            return ChromaDBClient(config)
        
        elif config.type == VectorDBType.PGVECTOR:
            logger.info(f"Creating PGVector client for collection '{config.collection_name}'")
            return PGVectorClient(config)
        
        elif config.type == VectorDBType.QDRANT:
            logger.info(f"Creating Qdrant client for collection '{config.collection_name}'")
            return QdrantClient(config)
        
        elif config.type == VectorDBType.MONGODB:
            # MongoDB support can be added in the future
            raise NotImplementedError(
                "MongoDB vector database support is not yet implemented. "
                "Supported databases: ChromaDB, PGVector, Qdrant"
            )
        
        else:
            raise ValueError(f"Unsupported vector database type: {config.type}")

    @staticmethod
    def create_client_for_autogen(
        config: VectorDBConfig
    ) -> dict[str, Any]:
        """Create vector database configuration for Autogen's RetrieveUserProxyAgent.
        
        This method creates the appropriate client and returns a configuration
        dictionary that can be passed to Autogen's retrieve_config.
        
        Uses ProviderAdapter if available for credential management.
        
        Args:
            config: Vector database configuration
            
        Returns:
            Dictionary with client and configuration for Autogen
        """
        # Use provider adapter if available for credential injection
        if _provider_adapter is not None and config.type == VectorDBType.QDRANT:
            if config.qdrant_config and config.qdrant_config.api_key:
                # Check if API key needs to be retrieved
                if config.qdrant_config.api_key.startswith("{{"):
                    key = config.qdrant_config.api_key.strip("{}").strip()
                    credential = _provider_adapter.get_credentials(
                        config.collection_name, key
                    )
                    if credential:
                        config.qdrant_config.api_key = credential
        
        client = VectorDBFactory.create_client(config)
        
        # Get or create the collection
        collection = client.get_or_create_collection(
            collection_name=config.collection_name,
            embedding_dimensions=config.embedding_dimensions,
            distance_metric=config.distance_metric
        )
        
        # Build Autogen-compatible configuration
        autogen_config = {
            "client": client.get_client(),
            "collection_name": config.collection_name,
            "embedding_model": config.embedding_model,
        }
        
        # Add database-specific configuration
        if config.type == VectorDBType.CHROMADB:
            # ChromaDB uses the client directly
            autogen_config["db_type"] = "chromadb"
        
        elif config.type == VectorDBType.PGVECTOR:
            # PGVector needs connection string
            if config.pgvector_config:
                autogen_config["db_type"] = "pgvector"
                autogen_config["connection_string"] = config.pgvector_config.connection_string
        
        elif config.type == VectorDBType.QDRANT:
            # Qdrant needs URL and optional API key
            if config.qdrant_config:
                autogen_config["db_type"] = "qdrant"
                if config.qdrant_config.url:
                    autogen_config["url"] = config.qdrant_config.url
                if config.qdrant_config.api_key:
                    autogen_config["api_key"] = config.qdrant_config.api_key
        
        logger.info(
            f"Created Autogen-compatible configuration for {config.type} "
            f"collection '{config.collection_name}'"
        )
        
        return autogen_config
