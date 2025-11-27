"""ChromaDB client implementation for vector storage."""

import logging
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.config import Settings

from src.config.vector_db_models import ChromaDBConfig, VectorDBConfig
from src.infrastructure.vector_db.base import VectorDBClient

logger = logging.getLogger(__name__)


class ChromaDBClient(VectorDBClient):
    """ChromaDB client for embedded vector storage."""

    def __init__(self, config: VectorDBConfig):
        """Initialize ChromaDB client.
        
        Args:
            config: Vector database configuration
        """
        if config.chromadb_config is None:
            config.chromadb_config = ChromaDBConfig()
        
        self.config = config
        self.chromadb_config = config.chromadb_config
        
        # Ensure persist directory exists
        persist_dir = Path(self.chromadb_config.persist_directory)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Create ChromaDB client with persistent storage
        client_settings = Settings(
            persist_directory=str(persist_dir),
            anonymized_telemetry=False,
        )
        
        # Apply additional client settings if provided
        if self.chromadb_config.client_settings:
            for key, value in self.chromadb_config.client_settings.items():
                setattr(client_settings, key, value)
        
        self._client = chromadb.Client(client_settings)
        logger.info(
            f"Initialized ChromaDB client with persist_directory: {persist_dir}"
        )

    def create_collection(
        self,
        collection_name: str,
        embedding_dimensions: int,
        distance_metric: str = "cosine",
        **kwargs: Any
    ) -> chromadb.Collection:
        """Create a new collection in ChromaDB.
        
        Args:
            collection_name: Name of the collection to create
            embedding_dimensions: Dimensionality of embedding vectors (not used by ChromaDB)
            distance_metric: Distance metric for similarity search
            **kwargs: Additional ChromaDB-specific parameters
            
        Returns:
            ChromaDB Collection object
        """
        # Map distance metric to ChromaDB format
        distance_map = {
            "cosine": "cosine",
            "euclidean": "l2",
            "l2": "l2",
            "dot_product": "ip",
            "ip": "ip"
        }
        
        chroma_distance = distance_map.get(distance_metric.lower(), "cosine")
        
        metadata = kwargs.get("metadata", {})
        metadata["embedding_dimensions"] = embedding_dimensions
        
        collection = self._client.create_collection(
            name=collection_name,
            metadata=metadata,
            embedding_function=None,  # We'll use Autogen's embedding
        )
        
        logger.info(
            f"Created ChromaDB collection '{collection_name}' "
            f"with distance metric '{chroma_distance}'"
        )
        return collection

    def get_collection(self, collection_name: str) -> Optional[chromadb.Collection]:
        """Get an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            ChromaDB Collection object or None if not found
        """
        try:
            collection = self._client.get_collection(
                name=collection_name,
                embedding_function=None
            )
            logger.debug(f"Retrieved ChromaDB collection '{collection_name}'")
            return collection
        except Exception as e:
            logger.warning(f"Collection '{collection_name}' not found: {e}")
            return None

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self._client.delete_collection(name=collection_name)
            logger.info(f"Deleted ChromaDB collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            return False

    def get_or_create_collection(
        self,
        collection_name: str,
        embedding_dimensions: int,
        distance_metric: str = "cosine",
        **kwargs: Any
    ) -> chromadb.Collection:
        """Get an existing collection or create it if it doesn't exist.
        
        Args:
            collection_name: Name of the collection
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional ChromaDB-specific parameters
            
        Returns:
            ChromaDB Collection object
        """
        collection = self.get_collection(collection_name)
        
        if collection is None:
            collection = self.create_collection(
                collection_name=collection_name,
                embedding_dimensions=embedding_dimensions,
                distance_metric=distance_metric,
                **kwargs
            )
            logger.info(f"Created new ChromaDB collection '{collection_name}'")
        else:
            logger.info(f"Using existing ChromaDB collection '{collection_name}'")
        
        return collection

    def get_client(self) -> chromadb.Client:
        """Get the underlying ChromaDB client.
        
        Returns:
            ChromaDB Client object
        """
        return self._client

    def close(self) -> None:
        """Close the database connection.
        
        ChromaDB doesn't require explicit connection closing for embedded mode.
        """
        logger.info("ChromaDB client closed")

    def list_collections(self) -> list[str]:
        """List all collections in the database.
        
        Returns:
            List of collection names
        """
        collections = self._client.list_collections()
        return [col.name for col in collections]

    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of documents in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of documents in the collection
        """
        collection = self.get_collection(collection_name)
        if collection is None:
            return 0
        return collection.count()
