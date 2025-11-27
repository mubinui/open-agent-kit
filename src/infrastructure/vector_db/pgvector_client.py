"""PGVector client implementation for PostgreSQL-based vector storage."""

import logging
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from src.config.vector_db_models import PGVectorConfig, VectorDBConfig
from src.infrastructure.vector_db.base import VectorDBClient

logger = logging.getLogger(__name__)

Base = declarative_base()


class PGVectorCollection:
    """Wrapper for PGVector collection operations."""

    def __init__(
        self,
        session: Session,
        table_name: str,
        vector_dimensions: int,
        model_class: type
    ):
        """Initialize PGVector collection wrapper.
        
        Args:
            session: SQLAlchemy session
            table_name: Name of the table
            vector_dimensions: Dimensionality of vectors
            model_class: SQLAlchemy model class for the table
        """
        self.session = session
        self.table_name = table_name
        self.vector_dimensions = vector_dimensions
        self.model_class = model_class

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: Optional[list[dict]] = None
    ) -> None:
        """Add documents with embeddings to the collection.
        
        Args:
            ids: List of document IDs
            embeddings: List of embedding vectors
            documents: List of document texts
            metadatas: Optional list of metadata dictionaries
        """
        if metadatas is None:
            metadatas = [{}] * len(ids)
        
        for doc_id, embedding, document, metadata in zip(ids, embeddings, documents, metadatas):
            record = self.model_class(
                id=doc_id,
                embedding=embedding,
                document=document,
                metadata=str(metadata)
            )
            self.session.merge(record)
        
        self.session.commit()

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: Optional[dict] = None
    ) -> dict:
        """Query the collection for similar vectors.
        
        Args:
            query_embeddings: List of query embedding vectors
            n_results: Number of results to return
            where: Optional metadata filter
            
        Returns:
            Dictionary with ids, distances, documents, and metadatas
        """
        results = {
            "ids": [],
            "distances": [],
            "documents": [],
            "metadatas": []
        }
        
        for query_embedding in query_embeddings:
            # Use cosine distance for similarity search
            query = self.session.query(
                self.model_class.id,
                self.model_class.document,
                self.model_class.metadata,
                self.model_class.embedding.cosine_distance(query_embedding).label("distance")
            ).order_by("distance").limit(n_results)
            
            query_results = query.all()
            
            ids = [r.id for r in query_results]
            distances = [float(r.distance) for r in query_results]
            documents = [r.document for r in query_results]
            metadatas = [r.metadata for r in query_results]
            
            results["ids"].append(ids)
            results["distances"].append(distances)
            results["documents"].append(documents)
            results["metadatas"].append(metadatas)
        
        return results

    def count(self) -> int:
        """Get the number of documents in the collection.
        
        Returns:
            Number of documents
        """
        return self.session.query(self.model_class).count()


class PGVectorClient(VectorDBClient):
    """PGVector client for PostgreSQL-based vector storage."""

    def __init__(self, config: VectorDBConfig):
        """Initialize PGVector client.
        
        Args:
            config: Vector database configuration
        """
        if config.pgvector_config is None:
            raise ValueError("pgvector_config is required for PGVector client")
        
        self.config = config
        self.pgvector_config = config.pgvector_config
        
        # Create SQLAlchemy engine
        self._engine = create_engine(
            self.pgvector_config.connection_string,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        # Create session factory
        self._session_factory = sessionmaker(bind=self._engine)
        
        # Enable pgvector extension
        with self._engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        
        logger.info(f"Initialized PGVector client with connection to PostgreSQL")
        
        # Store created model classes
        self._model_classes: dict[str, type] = {}

    def _create_model_class(
        self,
        table_name: str,
        vector_dimensions: int
    ) -> type:
        """Create a SQLAlchemy model class for a collection.
        
        Args:
            table_name: Name of the table
            vector_dimensions: Dimensionality of vectors
            
        Returns:
            SQLAlchemy model class
        """
        if table_name in self._model_classes:
            return self._model_classes[table_name]
        
        class VectorDocument(Base):
            __tablename__ = table_name
            
            id = Column(String, primary_key=True)
            embedding = Column(Vector(vector_dimensions))
            document = Column(Text)
            metadata = Column(Text)
        
        self._model_classes[table_name] = VectorDocument
        return VectorDocument

    def create_collection(
        self,
        collection_name: str,
        embedding_dimensions: int,
        distance_metric: str = "cosine",
        **kwargs: Any
    ) -> PGVectorCollection:
        """Create a new collection (table) in PostgreSQL.
        
        Args:
            collection_name: Name of the collection to create
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional parameters
            
        Returns:
            PGVectorCollection wrapper
        """
        model_class = self._create_model_class(collection_name, embedding_dimensions)
        
        # Create table
        Base.metadata.create_all(self._engine, tables=[model_class.__table__])
        
        # Create index for vector similarity search
        with self._engine.connect() as conn:
            # Create IVFFlat index for faster similarity search
            index_name = f"{collection_name}_embedding_idx"
            try:
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON {collection_name} USING ivfflat (embedding vector_cosine_ops) "
                    f"WITH (lists = 100)"
                ))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create IVFFlat index: {e}")
        
        session = self._session_factory()
        collection = PGVectorCollection(
            session=session,
            table_name=collection_name,
            vector_dimensions=embedding_dimensions,
            model_class=model_class
        )
        
        logger.info(
            f"Created PGVector collection '{collection_name}' "
            f"with {embedding_dimensions} dimensions"
        )
        return collection

    def get_collection(self, collection_name: str) -> Optional[PGVectorCollection]:
        """Get an existing collection.
        
        Args:
            collection_name: Name of the collection to retrieve
            
        Returns:
            PGVectorCollection wrapper or None if not found
        """
        # Check if table exists
        with self._engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS ("
                "SELECT FROM information_schema.tables "
                "WHERE table_name = :table_name"
                ")"
            ), {"table_name": collection_name})
            exists = result.scalar()
        
        if not exists:
            logger.warning(f"Collection '{collection_name}' not found")
            return None
        
        # Get vector dimensions from table
        with self._engine.connect() as conn:
            result = conn.execute(text(
                "SELECT atttypmod "
                "FROM pg_attribute "
                "WHERE attrelid = :table_name::regclass "
                "AND attname = 'embedding'"
            ), {"table_name": collection_name})
            typmod = result.scalar()
            vector_dimensions = typmod - 4 if typmod else self.config.embedding_dimensions
        
        model_class = self._create_model_class(collection_name, vector_dimensions)
        session = self._session_factory()
        
        collection = PGVectorCollection(
            session=session,
            table_name=collection_name,
            vector_dimensions=vector_dimensions,
            model_class=model_class
        )
        
        logger.debug(f"Retrieved PGVector collection '{collection_name}'")
        return collection

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection (drop table).
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {collection_name} CASCADE"))
                conn.commit()
            
            # Remove from model classes cache
            if collection_name in self._model_classes:
                del self._model_classes[collection_name]
            
            logger.info(f"Deleted PGVector collection '{collection_name}'")
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
    ) -> PGVectorCollection:
        """Get an existing collection or create it if it doesn't exist.
        
        Args:
            collection_name: Name of the collection
            embedding_dimensions: Dimensionality of embedding vectors
            distance_metric: Distance metric for similarity search
            **kwargs: Additional parameters
            
        Returns:
            PGVectorCollection wrapper
        """
        collection = self.get_collection(collection_name)
        
        if collection is None:
            collection = self.create_collection(
                collection_name=collection_name,
                embedding_dimensions=embedding_dimensions,
                distance_metric=distance_metric,
                **kwargs
            )
            logger.info(f"Created new PGVector collection '{collection_name}'")
        else:
            logger.info(f"Using existing PGVector collection '{collection_name}'")
        
        return collection

    def get_client(self) -> Any:
        """Get the underlying SQLAlchemy engine.
        
        Returns:
            SQLAlchemy Engine object
        """
        return self._engine

    def close(self) -> None:
        """Close the database connection."""
        self._engine.dispose()
        logger.info("PGVector client closed")

    def list_collections(self) -> list[str]:
        """List all collections (tables with vector columns).
        
        Returns:
            List of collection names
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.columns "
                "WHERE column_name = 'embedding' AND udt_name = 'vector'"
            ))
            return [row[0] for row in result]
