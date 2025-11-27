"""Base interface for vector database clients."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class VectorDBClient(ABC):
    """Abstract base class for vector database clients."""

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        embedding_dimensions: int,
        distance_metric: str = "cosine",
        **kwargs: Any
    ) -> Any:
        """Create a new collection in the vector database.
        
        Args:
            collection_name: Name of the collection to create
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional database-specific parameters
            
        Returns:
            Collection object or identifier
        """
        pass

    @abstractmethod
    def get_collection(self, collection_name: str) -> Any:
        """Get an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection object or None if not found
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_or_create_collection(
        self,
        collection_name: str,
        embedding_dimensions: int,
        distance_metric: str = "cosine",
        **kwargs: Any
    ) -> Any:
        """Get an existing collection or create it if it doesn't exist.
        
        Args:
            collection_name: Name of the collection
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional database-specific parameters
            
        Returns:
            Collection object or identifier
        """
        pass

    @abstractmethod
    def get_client(self) -> Any:
        """Get the underlying database client.
        
        Returns:
            Database client object
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""
        pass
