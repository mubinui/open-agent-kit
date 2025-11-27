"""Qdrant client implementation for vector storage."""

import logging
from pathlib import Path
from typing import Any, Optional

from qdrant_client import QdrantClient as QdrantClientLib
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from src.config.vector_db_models import QdrantConfig, VectorDBConfig
from src.infrastructure.vector_db.base import VectorDBClient

logger = logging.getLogger(__name__)


class QdrantClient(VectorDBClient):
    """Qdrant client for vector storage (local or cloud)."""

    def __init__(self, config: VectorDBConfig):
        """Initialize Qdrant client.
        
        Args:
            config: Vector database configuration
        """
        if config.qdrant_config is None:
            config.qdrant_config = QdrantConfig()
        
        self.config = config
        self.qdrant_config = config.qdrant_config
        
        # Determine connection mode
        if self.qdrant_config.url:
            # Remote Qdrant server
            self._client = QdrantClientLib(
                url=self.qdrant_config.url,
                api_key=self.qdrant_config.api_key,
                prefer_grpc=self.qdrant_config.prefer_grpc,
                timeout=self.qdrant_config.timeout
            )
            logger.info(f"Initialized Qdrant client with URL: {self.qdrant_config.url}")
        
        elif self.qdrant_config.path:
            # Local persistent storage
            path = Path(self.qdrant_config.path)
            path.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClientLib(path=str(path))
            logger.info(f"Initialized Qdrant client with local path: {path}")
        
        else:
            # In-memory mode
            self._client = QdrantClientLib(":memory:")
            logger.info("Initialized Qdrant client in memory mode")

    def _get_distance_metric(self, distance_metric: str) -> Distance:
        """Map distance metric to Qdrant Distance enum.
        
        Args:
            distance_metric: Distance metric name
            
        Returns:
            Qdrant Distance enum value
        """
        distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "l2": Distance.EUCLID,
            "dot_product": Distance.DOT,
            "ip": Distance.DOT,
        }
        return distance_map.get(distance_metric.lower(), Distance.COSINE)

    def create_collection(
        self,
        collection_name: str,
        embedding_dimensions: int,
        distance_metric: str = "cosine",
        **kwargs: Any
    ) -> str:
        """Create a new collection in Qdrant.
        
        Args:
            collection_name: Name of the collection to create
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional Qdrant-specific parameters
            
        Returns:
            Collection name
        """
        distance = self._get_distance_metric(distance_metric)
        
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dimensions,
                distance=distance
            )
        )
        
        logger.info(
            f"Created Qdrant collection '{collection_name}' "
            f"with {embedding_dimensions} dimensions and {distance_metric} distance"
        )
        return collection_name

    def get_collection(self, collection_name: str) -> Optional[str]:
        """Get an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            Collection name or None if not found
        """
        try:
            collection_info = self._client.get_collection(collection_name)
            if collection_info:
                logger.debug(f"Retrieved Qdrant collection '{collection_name}'")
                return collection_name
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
            self._client.delete_collection(collection_name)
            logger.info(f"Deleted Qdrant collection '{collection_name}'")
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
    ) -> str:
        """Get an existing collection or create it if it doesn't exist.
        
        Args:
            collection_name: Name of the collection
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional Qdrant-specific parameters
            
        Returns:
            Collection name
        """
        collection = self.get_collection(collection_name)
        
        if collection is None:
            collection = self.create_collection(
                collection_name=collection_name,
                embedding_dimensions=embedding_dimensions,
                distance_metric=distance_metric,
                **kwargs
            )
            logger.info(f"Created new Qdrant collection '{collection_name}'")
        else:
            logger.info(f"Using existing Qdrant collection '{collection_name}'")
        
        return collection

    def get_client(self) -> QdrantClientLib:
        """Get the underlying Qdrant client.
        
        Returns:
            QdrantClient object
        """
        return self._client

    def close(self) -> None:
        """Close the database connection."""
        # Qdrant client doesn't require explicit closing
        logger.info("Qdrant client closed")

    def list_collections(self) -> list[str]:
        """List all collections in the database.
        
        Returns:
            List of collection names
        """
        collections = self._client.get_collections()
        return [col.name for col in collections.collections]

    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of points in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of points in the collection
        """
        try:
            collection_info = self._client.get_collection(collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Failed to get count for collection '{collection_name}': {e}")
            return 0

    def add_points(
        self,
        collection_name: str,
        points: list[PointStruct]
    ) -> None:
        """Add points to a collection.
        
        Args:
            collection_name: Name of the collection
            points: List of PointStruct objects to add
        """
        self._client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.debug(f"Added {len(points)} points to collection '{collection_name}'")

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> list[dict]:
        """Search for similar vectors in a collection.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of search results with id, score, and payload
        """
        results = self._client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
        
        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
