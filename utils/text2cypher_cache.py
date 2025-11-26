"""
LRU Cache for Text2Cypher results.
"""

import hashlib
import json
from collections import OrderedDict
from typing import Any, Optional, Dict


class Text2CypherCache:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _generate_key(self, question: str, schema: dict) -> str:
        question_hash = hashlib.sha256(question.encode()).hexdigest()[:16]
        schema_str = json.dumps(schema, sort_keys=True)
        schema_hash = hashlib.sha256(schema_str.encode()).hexdigest()[:16]
        return f"{question_hash}_{schema_hash}"

    def get(self, question: str, schema: dict) -> Optional[Dict[str, Any]]:
        key = self._generate_key(question, schema)
        if key in self.cache:
            self.hits += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, question: str, schema: dict, result: Dict[str, Any]) -> None:
        key = self._generate_key(question, schema)
        
        if key in self.cache:
            self.cache.move_to_end(key)
        
        self.cache[key] = result
        
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
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
        return len(self.cache)
