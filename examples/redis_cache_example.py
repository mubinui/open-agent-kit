"""Example demonstrating Redis caching layer usage."""

import os
from uuid import uuid4
from datetime import datetime

from src.infrastructure.cache import RedisCache
from src.infrastructure.session_cache import SessionCache
from src.infrastructure.embedding_cache import EmbeddingCache
from src.infrastructure.llm_cache import LLMCacheMonitor, AutogenCacheConfig
from src.infrastructure.cache_manager import CacheManager
from src.memory.models import ConversationState, MessageRole


def main():
    """Demonstrate Redis caching functionality."""
    
    # Get Redis connection details from environment
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))
    
    print(f"Connecting to Redis at {redis_host}:{redis_port}/{redis_db}")
    
    # Initialize Redis cache
    redis_cache = RedisCache(
        host=redis_host,
        port=redis_port,
        db=redis_db,
    )
    
    # Test connection
    if not redis_cache.ping():
        print("❌ Failed to connect to Redis")
        print("Make sure Redis is running: docker run -d -p 6379:6379 redis:latest")
        return
    
    print("✓ Connected to Redis successfully\n")
    
    # ========================================
    # 1. Session Caching Example
    # ========================================
    print("=" * 60)
    print("1. Session Caching Example")
    print("=" * 60)
    
    session_cache = SessionCache(redis_cache, session_ttl=3600)
    
    # Create a test session
    session = ConversationState(
        session_id=uuid4(),
        turn_count=0,
        active=True,
        metadata={"user_id": "user123", "workflow_id": "test_workflow"}
    )
    
    # Add some messages
    session.add_message(MessageRole.USER, "Hello, how are you?")
    session.add_message(MessageRole.ASSISTANT, "I'm doing well, thank you!")
    session.increment_turn()
    
    print(f"Created session: {session.session_id}")
    
    # Cache the session
    session_cache.set(session)
    print("✓ Session cached")
    
    # Retrieve from cache
    cached_session = session_cache.get(session.session_id)
    if cached_session:
        print(f"✓ Session retrieved from cache")
        print(f"  - Turn count: {cached_session.turn_count}")
        print(f"  - Messages: {len(cached_session.messages)}")
        print(f"  - Active: {cached_session.active}")
    
    # Get session metadata
    metadata = session_cache.get_session_metadata(session.session_id)
    print(f"✓ Session metadata: {metadata}")
    
    print()
    
    # ========================================
    # 2. Embedding Caching Example
    # ========================================
    print("=" * 60)
    print("2. Embedding Caching Example")
    print("=" * 60)
    
    embedding_cache = EmbeddingCache(redis_cache, embedding_ttl=86400)
    
    # Simulate embedding vectors
    test_content = "This is a test document for embedding caching"
    test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 100  # 500-dim vector
    model_name = "all-mpnet-base-v2"
    
    print(f"Content: {test_content}")
    print(f"Model: {model_name}")
    print(f"Embedding dimension: {len(test_embedding)}")
    
    # Cache the embedding
    embedding_cache.set(test_content, test_embedding, model_name)
    print("✓ Embedding cached")
    
    # Retrieve from cache
    cached_embedding = embedding_cache.get(test_content, model_name)
    if cached_embedding:
        print(f"✓ Embedding retrieved from cache")
        print(f"  - Dimension: {len(cached_embedding)}")
        print(f"  - First 5 values: {cached_embedding[:5]}")
    
    # Get cache stats
    stats = embedding_cache.get_cache_stats()
    print(f"✓ Cache stats: {stats}")
    
    print()
    
    # ========================================
    # 3. LLM Cache Monitoring Example
    # ========================================
    print("=" * 60)
    print("3. LLM Cache Monitoring Example")
    print("=" * 60)
    
    llm_monitor = LLMCacheMonitor(redis_cache, enable_metrics=True)
    
    # Simulate some LLM requests
    print("Simulating LLM requests...")
    llm_monitor.record_request(cache_hit=False, tokens_saved=0, cost_saved=0.0)
    llm_monitor.record_request(cache_hit=True, tokens_saved=500, cost_saved=0.01)
    llm_monitor.record_request(cache_hit=True, tokens_saved=300, cost_saved=0.006)
    llm_monitor.record_request(cache_hit=False, tokens_saved=0, cost_saved=0.0)
    llm_monitor.record_request(cache_hit=True, tokens_saved=450, cost_saved=0.009)
    
    # Get metrics
    metrics = llm_monitor.get_metrics()
    print(f"✓ LLM Cache Metrics:")
    print(f"  - Total requests: {metrics.total_requests}")
    print(f"  - Cache hits: {metrics.cache_hits}")
    print(f"  - Cache misses: {metrics.cache_misses}")
    print(f"  - Hit rate: {metrics.hit_rate:.2f}%")
    print(f"  - Tokens saved: {metrics.total_tokens_saved}")
    print(f"  - Cost saved: ${metrics.total_cost_saved:.4f}")
    
    # Demonstrate Autogen cache config
    print("\n✓ Autogen Cache Configuration:")
    llm_config = AutogenCacheConfig.create_llm_config_with_cache(
        config_list=[{"model": "gpt-4", "api_key": "test"}],
        temperature=0.7,
        cache_seed=42,
    )
    print(f"  - Cache enabled: {AutogenCacheConfig.is_cache_enabled(llm_config)}")
    print(f"  - Cache seed: {llm_config.get('cache_seed')}")
    
    print()
    
    # ========================================
    # 4. Cache Manager Example
    # ========================================
    print("=" * 60)
    print("4. Cache Manager Example")
    print("=" * 60)
    
    cache_manager = CacheManager(
        redis_cache=redis_cache,
        session_cache=session_cache,
        embedding_cache=embedding_cache,
        llm_cache_monitor=llm_monitor,
    )
    
    # Get overall cache metrics
    all_metrics = cache_manager.get_cache_metrics()
    print("✓ Overall Cache Metrics:")
    print(f"  - Sessions: {all_metrics['sessions']}")
    print(f"  - Embeddings: {all_metrics['embeddings']}")
    print(f"  - LLM: {all_metrics['llm']}")
    print(f"  - Redis connected: {all_metrics['redis']['connected']}")
    
    # Demonstrate cache invalidation
    print("\n✓ Cache Invalidation:")
    print(f"  - Invalidating session {session.session_id}...")
    cache_manager.invalidate_session(session.session_id)
    
    # Verify session is gone
    if not session_cache.exists(session.session_id):
        print("  - Session successfully invalidated")
    
    print()
    
    # ========================================
    # Cleanup
    # ========================================
    print("=" * 60)
    print("Cleanup")
    print("=" * 60)
    
    # Clear all test data
    session_cache.clear_all_sessions()
    embedding_cache.clear_all_embeddings()
    llm_monitor.reset_metrics()
    
    print("✓ All test data cleared")
    
    # Close Redis connection
    redis_cache.close()
    print("✓ Redis connection closed")
    
    print("\n" + "=" * 60)
    print("Redis Caching Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
