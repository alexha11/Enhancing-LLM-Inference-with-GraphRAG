"""Cypher Query Validator and Post-Processor.

This module provides validation and post-processing capabilities for Cypher queries
to ensure they are syntactically valid and follow best practices.
"""

import re
from typing import Optional


class CypherQueryValidator:
    """Validates and post-processes Cypher queries."""

    def __init__(self, db_connection):
        """Initialize validator with database connection.
        
        Args:
            db_connection: Kuzu database connection for dry-run validation
        """
        self.conn = db_connection

    def validate_syntax(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate query syntax using EXPLAIN (dry-run).
        
        Args:
            query: Cypher query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Use EXPLAIN to check syntax without executing
            explain_query = f"EXPLAIN {query}"
            self.conn.execute(explain_query)
            return True, None
        except Exception as e:
            return False, str(e)

    def post_process(self, query: str) -> str:
        """Apply rule-based post-processing to the query.
        
        Rules:
        - Enforce lowercase comparisons with lower()
        - Ensure WHERE clauses use CONTAINS for string matching
        - Fix common syntax issues
        - Ensure proper property projection in RETURN clauses
        
        Args:
            query: Raw Cypher query
            
        Returns:
            Post-processed query
        """
        processed_query = query.strip()
        
        # 1. Ensure string comparisons use to_lower() and CONTAINS
        processed_query = self._enforce_lowercase_comparisons(processed_query)
        
        # 2. Ensure proper property projection in RETURN
        processed_query = self._fix_return_projection(processed_query)
        
        # 3. Remove any newlines or excessive whitespace
        processed_query = re.sub(r'\s+', ' ', processed_query)

        # 4. Explicitly replace to_lower with lower (if any slipped through)
        processed_query = processed_query.replace('to_lower(', 'lower(')
        
        return processed_query

    def _enforce_lowercase_comparisons(self, query: str) -> str:
        """Ensure string comparisons use lower() and CONTAINS.
        
        Args:
            query: Cypher query
            
        Returns:
            Query with enforced lowercase comparisons
        """
        # Pattern to match WHERE clauses with string comparisons
        # This is a simplified approach - in production you'd want more robust parsing
        
        # Look for patterns like: property = 'value' or property CONTAINS 'value'
        # and ensure lower() is used
        
        # Match: WHERE <prop> = 'value' or WHERE <prop> CONTAINS 'value'
        # Without lower() wrapper
        patterns = [
            # Match: property = 'value' (without lower)
            (r"(\w+\.\w+)\s*=\s*'([^']+)'", r"lower(\1) CONTAINS '\2'"),
            # Match: property CONTAINS 'value' (without lower)
            (r"(?<!lower\()(\w+\.\w+)\s+CONTAINS\s+'([^']+)'", r"lower(\1) CONTAINS '\2'"),
        ]
        
        result = query
        for pattern, replacement in patterns:
            # Check if the property already has lower
            matches = re.finditer(pattern, result, re.IGNORECASE)
            for match in matches:
                original = match.group(0)
                # Only replace if 'lower' is not already present before this match
                if 'lower' not in result[max(0, match.start()-20):match.start()].lower():
                    new_text = re.sub(pattern, replacement, original, flags=re.IGNORECASE)
                    result = result.replace(original, new_text, 1)
        
        return result

    def _fix_return_projection(self, query: str) -> str:
        """Ensure RETURN clause projects properties, not full nodes/relationships.
        
        Args:
            query: Cypher query
            
        Returns:
            Query with fixed RETURN projection
        """
        # Look for RETURN statements that return nodes without properties
        # Pattern: RETURN <variable> (without property access)
        # This is a basic implementation - may need refinement
        
        # Match RETURN clause
        return_match = re.search(r'\bRETURN\b(.+?)(?:ORDER BY|LIMIT|$)', query, re.IGNORECASE)
        if not return_match:
            return query
        
        return_clause = return_match.group(1).strip()
        
        # Check if returning full nodes (no dots in variable names)
        # Skip if already has properties (contains dots) or functions (contains parentheses)
        items = [item.strip() for item in return_clause.split(',')]
        needs_fix = False
        
        for item in items:
            # Check if it's a simple variable without property access
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', item.split()[0]):
                # This might be a full node/relationship return
                needs_fix = True
                break
        
        # For now, return as is - fixing this requires knowledge of node properties
        # which would need schema context. This is left as a placeholder.
        return query


class CypherSelfRefinement:
    """Self-refinement loop for Cypher query generation."""

    def __init__(self, validator: CypherQueryValidator, max_attempts: int = 3):
        """Initialize self-refinement with validator.
        
        Args:
            validator: CypherQueryValidator instance
            max_attempts: Maximum number of refinement attempts
        """
        self.validator = validator
        self.max_attempts = max_attempts

    def refine(self, query: str, repair_fn=None) -> tuple[str, bool, list[str]]:
        """Apply self-refinement loop: generate → validate → repair.
        
        Args:
            query: Initial Cypher query
            repair_fn: Optional function to repair invalid queries
            
        Returns:
            Tuple of (final_query, is_valid, error_history)
        """
        current_query = query
        error_history = []
        
        for attempt in range(self.max_attempts):
            # Post-process the query
            processed_query = self.validator.post_process(current_query)
            
            # Validate syntax
            is_valid, error_msg = self.validator.validate_syntax(processed_query)
            
            if is_valid:
                return processed_query, True, error_history
            
            # Track error
            error_history.append(f"Attempt {attempt + 1}: {error_msg}")
            
            # Try to repair if repair function provided
            if repair_fn:
                current_query = repair_fn(current_query, error_msg)
            else:
                # Simple heuristic repairs
                current_query = self._apply_heuristic_repairs(current_query, error_msg)
        
        # Return last attempt even if invalid
        return processed_query, False, error_history

    def _apply_heuristic_repairs(self, query: str, error_msg: str) -> str:
        """Apply simple heuristic repairs based on error message.
        
        Args:
            query: Query to repair
            error_msg: Error message from validation
            
        Returns:
            Potentially repaired query
        """
        # Basic heuristics for common errors
        repaired = query
        
        # Fix missing semicolon (if required)
        if 'semicolon' in error_msg.lower():
            repaired = repaired.rstrip(';') + ';'
        
        # Fix APOC usage (not supported in Kuzu)
        if 'apoc' in repaired.lower():
            # Remove APOC calls - this is a simplified approach
            repaired = re.sub(r'CALL apoc\.[^\s]+', '', repaired, flags=re.IGNORECASE)
        
        return repaired
