"""
- Checking if a Cypher query is valid 
- Fixing common mistakes in the query
- Automatically repairing wrong queries
"""

import re
from typing import Optional


class CypherQueryValidator:
    def __init__(self, db_connection):
        self.conn = db_connection

    #Run EXPLAIN {query} in Kuzu
    def validate_syntax(self, query: str) -> tuple[bool, Optional[str]]:
        try:
            explain_query = f"EXPLAIN {query}"
            self.conn.execute(explain_query)
            return True, None
        except Exception as error:
            return False, str(error)

    def post_process(self, query: str) -> str:
        processed_query = query.strip()
        
        processed_query = self._enforce_lowercase_comparisons(processed_query)
        
        processed_query = self._fix_return_projection(processed_query)
        
        processed_query = re.sub(r'\s+', ' ', processed_query)

        processed_query = processed_query.replace('to_lower(', 'lower(')
        
        return processed_query

    def _enforce_lowercase_comparisons(self, query: str) -> str:
        patterns = [
            (r"(\w+\.\w+)\s*=\s*'([^']+)'", r"lower(\1) CONTAINS '\2'"),
            (r"(?<!lower\()(\w+\.\w+)\s+CONTAINS\s+'([^']+)'", r"lower(\1) CONTAINS '\2'"),
        ]
        
        result = query
        for pattern, replacement in patterns:
            matches = re.finditer(pattern, result, re.IGNORECASE)
            for match in matches:
                original = match.group(0)
                if 'lower' not in result[max(0, match.start()-20):match.start()].lower():
                    new_text = re.sub(pattern, replacement, original, flags=re.IGNORECASE)
                    result = result.replace(original, new_text, 1)
        
        return result

    def _fix_return_projection(self, query: str) -> str:
        return_match = re.search(r'\bRETURN\b(.+?)(?:ORDER BY|LIMIT|$)', query, re.IGNORECASE)
        if not return_match:
            return query
        
        return_clause = return_match.group(1).strip()
        
        items = [item.strip() for item in return_clause.split(',')]

        for item in items:
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', item.split()[0]):
                break
        
        return query


class CypherSelfRefinement:
    def __init__(self, validator: CypherQueryValidator, max_attempts: int = 3):
        self.validator = validator
        self.max_attempts = max_attempts

    def refine(self, query: str, repair_fn=None) -> tuple[str, bool, list[str]]:
        current_query = query
        error_history = []
        
        for attempt in range(self.max_attempts):
            processed_query = self.validator.post_process(current_query)
            
            is_valid, error_msg = self.validator.validate_syntax(processed_query)
            
            if is_valid:
                return processed_query, True, error_history
            
            error_history.append(f"Attempt {attempt + 1}: {error_msg}")
            
            if repair_fn:
                current_query = repair_fn(current_query, error_msg)
            else:
                current_query = self._apply_hexuristic_repairs(current_query, error_msg)
        
        return processed_query, False, error_history

    def _apply_heuristic_repairs(self, query: str, error_msg: str) -> str:
        repaired = query
        
        if 'semicolon' in error_msg.lower():
            repaired = repaired.rstrip(';') + ';'
        
        if 'apoc' in repaired.lower():
            repaired = re.sub(r'CALL apoc\.[^\s]+', '', repaired, flags=re.IGNORECASE)
        
        return repaired
