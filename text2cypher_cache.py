"""LRU Cache for Text2Cypher results.

This module provides an LRU (Least Recently Used) cache for storing
and retrieving Text2Cypher query results, keyed by question hash and schema hash.
"""

import hashlib
import json
from collections import OrderedDict
from typing import Any, Optional, Dict, List


class Text2CypherCache:
    """LRU Cache for Text2Cypher results."""

    def __init__(self, max_size: int = 100):
        """Initialize the cache with a maximum size.
        
        Args:
            max_size: Maximum number of entries to store in cache
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _generate_key(self, question: str, schema: dict) -> str:
        """Generate a cache key from question and schema.
        
        Args:
            question: The user's question
            schema: The graph schema dictionary
            
        Returns:
            A hash string combining question and schema
        """
        question_hash = hashlib.sha256(question.encode()).hexdigest()[:16]
        schema_str = json.dumps(schema, sort_keys=True)
        schema_hash = hashlib.sha256(schema_str.encode()).hexdigest()[:16]
        return f"{question_hash}_{schema_hash}"

    def get(self, question: str, schema: dict) -> Optional[Dict[str, Any]]:
        """Retrieve a cached result.
        
        Args:
            question: The user's question
            schema: The graph schema dictionary
            
        Returns:
            Cached result if found, None otherwise
        """
        key = self._generate_key(question, schema)
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, question: str, schema: dict, result: Dict[str, Any]) -> None:
        """Store a result in the cache.
        
        Args:
            question: The user's question
            schema: The graph schema dictionary
            result: The result to cache (contains query, context, etc.)
        """
        key = self._generate_key(question, schema)
        
        # If key exists, update and move to end
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = result
        
        # Prune if over capacity
        if len(self.cache) > self.max_size:
            # Remove least recently used (first item)
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }

    def __len__(self) -> int:
        """Return the current cache size."""
        return len(self.cache)
