"""Cache manager for coordinating cache invalidation and warming strategies."""

import logging
from typing import Optional, Any
from uuid import UUID
from datetime import datetime, timedelta

from src.infrastructure.cache import RedisCache
from src.infrastructure.session_cache import SessionCache
from src.infrastructure.embedding_cache import EmbeddingCache
from src.infrastructure.llm_cache import LLMCacheMonitor

logger = logging.getLogger(__name__)


class CacheInvalidationStrategy:
    """Base class for cache invalidation strategies."""
    
    def should_invalidate(self, key: str, metadata: dict[str, Any]) -> bool:
        """Determine if a cache entry should be invalidated.

        Args:
            key: Cache key
            metadata: Cache entry metadata

        Returns:
            True if entry should be invalidated, False otherwise
        """
        raise NotImplementedError


class TimeBasedInvalidation(CacheInvalidationStrategy):
    """Invalidate cache entries based on age."""
    
    def __init__(self, max_age_seconds: int):
        """Initialize time-based invalidation.

        Args:
            max_age_seconds: Maximum age in seconds before invalidation
        """
        self.max_age_seconds = max_age_seconds
    
    def should_invalidate(self, key: str, metadata: dict[str, Any]) -> bool:
        """Check if entry is older than max age."""
        created_at = metadata.get('created_at')
        if not created_at:
            return False
        
        try:
            created_time = datetime.fromisoformat(created_at)
            age = (datetime.utcnow() - created_time).total_seconds()
            return age > self.max_age_seconds
        except (ValueError, TypeError):
            return False


class CacheManager:
    """
    Manager for coordinating cache operations across different cache types.
    
    Handles:
    - Cache invalidation strategies
    - Cache warming
    - Cache metrics and monitoring
    - Coordinated cache operations
    """

    def __init__(
        self,
        redis_cache: RedisCache,
        session_cache: Optional[SessionCache] = None,
        embedding_cache: Optional[EmbeddingCache] = None,
        llm_cache_monitor: Optional[LLMCacheMonitor] = None,
    ):
        """Initialize cache manager.

        Args:
            redis_cache: Redis cache client
            session_cache: Optional session cache
            embedding_cache: Optional embedding cache
            llm_cache_monitor: Optional LLM cache monitor
        """
        self.redis_cache = redis_cache
        self.session_cache = session_cache or SessionCache(redis_cache)
        self.embedding_cache = embedding_cache or EmbeddingCache(redis_cache)
        self.llm_cache_monitor = llm_cache_monitor
        
        logger.info("Cache manager initialized")

    def invalidate_session(self, session_id: UUID) -> bool:
        """Invalidate session cache.

        Args:
            session_id: Session identifier

        Returns:
            True if invalidated, False otherwise
        """
        logger.info(f"Invalidating session cache: {session_id}")
        return self.session_cache.delete(session_id)

    def invalidate_sessions_by_user(self, user_id: str) -> int:
        """Invalidate all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions invalidated
        """
        logger.info(f"Invalidating sessions for user: {user_id}")
        
        count = 0
        session_ids = self.session_cache.get_all_session_ids()
        
        for session_id in session_ids:
            metadata = self.session_cache.get_session_metadata(session_id)
            if metadata and metadata.get('metadata', {}).get('user_id') == user_id:
                if self.session_cache.delete(session_id):
                    count += 1
        
        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count

    def invalidate_embedding(self, content: str, model: str = "default") -> bool:
        """Invalidate embedding cache.

        Args:
            content: Text content
            model: Embedding model name

        Returns:
            True if invalidated, False otherwise
        """
        logger.debug(f"Invalidating embedding cache (model={model})")
        return self.embedding_cache.delete(content, model)

    def invalidate_embeddings_by_model(self, model: str) -> int:
        """Invalidate all embeddings for a specific model.

        Args:
            model: Embedding model name

        Returns:
            Number of embeddings invalidated
        """
        logger.info(f"Invalidating embeddings for model: {model}")
        
        count = 0
        hashes = self.embedding_cache.get_all_embedding_hashes()
        
        for content_hash in hashes:
            data = self.embedding_cache.get_by_hash(content_hash)
            if data and data.get('model') == model:
                if self.embedding_cache.delete_by_hash(content_hash):
                    count += 1
        
        logger.info(f"Invalidated {count} embeddings for model {model}")
        return count

    def invalidate_all_sessions(self) -> int:
        """Invalidate all session caches.

        Returns:
            Number of sessions invalidated
        """
        logger.warning("Invalidating all session caches")
        return self.session_cache.clear_all_sessions()

    def invalidate_all_embeddings(self) -> int:
        """Invalidate all embedding caches.

        Returns:
            Number of embeddings invalidated
        """
        logger.warning("Invalidating all embedding caches")
        return self.embedding_cache.clear_all_embeddings()

    def invalidate_all_caches(self) -> dict[str, int]:
        """Invalidate all caches.

        Returns:
            Dictionary with counts of invalidated entries by cache type
        """
        logger.warning("Invalidating all caches")
        
        return {
            'sessions': self.invalidate_all_sessions(),
            'embeddings': self.invalidate_all_embeddings(),
        }

    def warm_session_cache(
        self,
        session_ids: list[UUID],
        fetch_callback: Any,
    ) -> int:
        """Warm session cache by pre-loading sessions.

        Args:
            session_ids: List of session IDs to warm
            fetch_callback: Callback function to fetch session data

        Returns:
            Number of sessions warmed
        """
        logger.info(f"Warming session cache for {len(session_ids)} sessions")
        
        count = 0
        for session_id in session_ids:
            try:
                # Check if already cached
                if self.session_cache.exists(session_id):
                    continue
                
                # Fetch session data
                session = fetch_callback(session_id)
                if session:
                    # Cache the session
                    if self.session_cache.set(session):
                        count += 1
            except Exception as e:
                logger.error(
                    f"Failed to warm session cache for {session_id}: {e}",
                    exc_info=True,
                )
        
        logger.info(f"Warmed {count} sessions in cache")
        return count

    def warm_embedding_cache(
        self,
        contents: list[str],
        fetch_callback: Any,
        model: str = "default",
    ) -> int:
        """Warm embedding cache by pre-computing embeddings.

        Args:
            contents: List of text contents to warm
            fetch_callback: Callback function to fetch embeddings
            model: Embedding model name

        Returns:
            Number of embeddings warmed
        """
        logger.info(
            f"Warming embedding cache for {len(contents)} contents (model={model})"
        )
        
        count = 0
        for content in contents:
            try:
                # Check if already cached
                if self.embedding_cache.exists(content, model):
                    continue
                
                # Fetch embedding
                embedding = fetch_callback(content, model)
                if embedding:
                    # Cache the embedding
                    if self.embedding_cache.set(content, embedding, model):
                        count += 1
            except Exception as e:
                logger.error(
                    f"Failed to warm embedding cache: {e}",
                    exc_info=True,
                )
        
        logger.info(f"Warmed {count} embeddings in cache")
        return count

    def get_cache_metrics(self) -> dict[str, Any]:
        """Get metrics for all caches.

        Returns:
            Dictionary with cache metrics
        """
        metrics = {
            'sessions': {
                'total': len(self.session_cache.get_all_session_ids()),
                'ttl_seconds': self.session_cache.session_ttl,
            },
            'embeddings': self.embedding_cache.get_cache_stats(),
        }
        
        # Add LLM cache metrics if monitor is available
        if self.llm_cache_monitor:
            llm_metrics = self.llm_cache_monitor.get_metrics()
            metrics['llm'] = llm_metrics.to_dict()
        
        # Add Redis connection status
        metrics['redis'] = {
            'connected': self.redis_cache.ping(),
        }
        
        return metrics

    def apply_invalidation_strategy(
        self,
        strategy: CacheInvalidationStrategy,
        cache_type: str = "all",
    ) -> dict[str, int]:
        """Apply invalidation strategy to caches.

        Args:
            strategy: Invalidation strategy to apply
            cache_type: Type of cache to apply to ("sessions", "embeddings", "all")

        Returns:
            Dictionary with counts of invalidated entries by cache type
        """
        logger.info(
            f"Applying invalidation strategy to {cache_type} cache(s)"
        )
        
        results = {}
        
        # Apply to session cache
        if cache_type in ("sessions", "all"):
            count = 0
            session_ids = self.session_cache.get_all_session_ids()
            
            for session_id in session_ids:
                metadata = self.session_cache.get_session_metadata(session_id)
                if metadata and strategy.should_invalidate(
                    str(session_id), metadata
                ):
                    if self.session_cache.delete(session_id):
                        count += 1
            
            results['sessions'] = count
            logger.info(f"Invalidated {count} sessions using strategy")
        
        # Apply to embedding cache
        if cache_type in ("embeddings", "all"):
            count = 0
            hashes = self.embedding_cache.get_all_embedding_hashes()
            
            for content_hash in hashes:
                data = self.embedding_cache.get_by_hash(content_hash)
                if data and strategy.should_invalidate(content_hash, data):
                    if self.embedding_cache.delete_by_hash(content_hash):
                        count += 1
            
            results['embeddings'] = count
            logger.info(f"Invalidated {count} embeddings using strategy")
        
        return results

    def schedule_periodic_invalidation(
        self,
        interval_seconds: int,
        max_age_seconds: int,
    ) -> None:
        """Schedule periodic cache invalidation based on age.

        Args:
            interval_seconds: Interval between invalidation runs
            max_age_seconds: Maximum age before invalidation

        Note:
            This is a placeholder for future implementation with a task scheduler.
            In production, use a task queue (Celery, APScheduler, etc.)
        """
        logger.info(
            f"Periodic invalidation configured: "
            f"interval={interval_seconds}s, max_age={max_age_seconds}s"
        )
        
        # TODO: Implement with task scheduler
        # For now, just log the configuration
        strategy = TimeBasedInvalidation(max_age_seconds)
        logger.info(
            "Periodic invalidation requires task scheduler integration "
            "(not yet implemented)"
        )


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(redis_cache: Optional[RedisCache] = None) -> CacheManager:
    """Get the singleton cache manager instance.

    Args:
        redis_cache: Optional Redis cache client

    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        if redis_cache is None:
            raise ValueError("redis_cache required for first initialization")
        _cache_manager = CacheManager(redis_cache)
        logger.info("Initialized cache manager")
    return _cache_manager
