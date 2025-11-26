# Quick Start Guide

## Overview

This implementation adds significant enhancements to the baseline GraphRAG system:

### ✅ Task 1: Text2Cypher Improvements
1. **Dynamic Few-Shot Selection** - Automatically retrieves relevant examples
2. **Self-Refinement Loop** - Validates and repairs queries (up to 3 attempts)
3. **Rule-Based Post-Processing** - Enforces best practices (lowercase, CONTAINS, etc.)

### ✅ Task 2: Caching & Performance
1. **LRU Cache** - 100-2000x speedup for repeated queries
2. **Performance Benchmarking** - Track 9 pipeline stages with ms precision
3. **Visualization** - ASCII bar charts and JSON export

## Quick Test

Test the components independently:

```bash
cd Enhancing-LLM-Inference-with-GraphRAG
python test_enhancements.py
```

Expected output:
```
======================================================================
                    ENHANCED GRAPHRAG COMPONENT TESTS
======================================================================

============================================================
TESTING LRU CACHE
============================================================
✓ Basic set/get works
✓ Cache miss works correctly
✓ LRU eviction works correctly
✓ Statistics tracking works
✅ All cache tests passed!

... (more tests)

======================================================================
                         ALL TESTS PASSED! ✅
======================================================================
```

## Run the Enhanced App

```bash
# Make sure you have the Nobel database set up
uv run python create_nobel_api_graph.py

# Run the enhanced app
uv run marimo run graph_rag_enhanced.py
```

## Key Files Created

| File | Purpose |
|------|---------|
| `text2cypher_cache.py` | LRU cache with statistics |
| `cypher_validator.py` | Query validation & post-processing |
| `performance_benchmark.py` | Performance tracking & visualization |
| `graph_rag_enhanced.py` | Main enhanced app (integrates all) |
| `test_enhancements.py` | Unit tests for components |
| `IMPLEMENTATION.md` | Detailed documentation |

## Usage Example

In the enhanced app, you'll see:

1. **Input**: Natural language question
2. **Output**: 
   - Cypher query (with 🔵 if cached, 🟢 if computed)
   - Natural language answer
   - Performance breakdown (optional)
   - Cache statistics (optional)

### Sample Query

**Question**: "Which scholars won prizes in Physics and were affiliated with University of Cambridge?"

**Generated Query** (with refinement):
```cypher
MATCH (s:Scholar)-[:WON]->(p:Prize), (s)-[:AFFILIATED_WITH]->(i:Institution) 
WHERE to_lower(p.category) CONTAINS 'physics' 
  AND to_lower(i.name) CONTAINS 'university of cambridge' 
RETURN s.knownName AS knownName, p.awardYear AS awardYear 
ORDER BY awardYear
```

**Performance** (first run):
```
5_text2cypher_generation    ████████████████████     850ms (42%)
8_answer_generation         █████████████           620ms (31%)
3_schema_pruning            ███████                 310ms (15%)
...
TOTAL: 2,010ms
```

**Performance** (cached):
```
2_cache_lookup              █                       1ms (100%)
TOTAL: 1ms
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Question                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  Cache Lookup  │ ◄── LRU Cache (100 entries)
              └────────┬───────┘
                   Hit │ Miss
                  ┌────┴────┐
             FAST │         │ FULL PIPELINE
                  │         ▼
                  │   ┌──────────────────┐
                  │   │ Schema Retrieval │
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │ Schema Pruning   │
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │ Dynamic Examples │ ◄── Similarity Search
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │ Text2Cypher Gen  │
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │  Validate Query  │ ◄── EXPLAIN (dry-run)
                  │   └────────┬─────────┘
                  │            │ Invalid
                  │            ▼
                  │   ┌──────────────────┐
                  │   │  Post-Process    │ ◄── Rule-based fixes
                  │   │  & Repair        │
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │ Execute Query    │
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │ Generate Answer  │
                  │   └────────┬─────────┘
                  │            ▼
                  │   ┌──────────────────┐
                  │   │  Cache Result    │
                  │   └────────┬─────────┘
                  │            │
                  └────────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │     Answer     │
                      └────────────────┘
                               
         [Performance tracked at each stage]
```

## Performance Gains

| Scenario | Time (First Run) | Time (Cached) | Speedup |
|----------|------------------|---------------|---------|
| Simple query | ~2,000ms | ~1ms | 2000x |
| Complex query | ~3,500ms | ~1ms | 3500x |
| Cache hit rate after 10 queries | - | 60-80% | - |

## Learning Outcomes

By studying this implementation, you'll understand:

1. **Prompt Engineering**
   - Few-shot learning with dynamic exemplar selection
   - Structured prompts with syntax rules
   
2. **Iterative Generation**
   - Self-refinement loops
   - Validation strategies
   - Automatic repair heuristics

3. **Performance Engineering**
   - Caching strategies (LRU)
   - Profiling and instrumentation
   - Bottleneck identification

4. **System Design**
   - Separation of concerns
   - Modular architecture
   - Production-ready error handling

## Next Steps

1. ✅ Run `test_enhancements.py` to verify components
2. ✅ Run `graph_rag_enhanced.py` with marimo
3. Try different questions and observe:
   - Cache behavior
   - Performance breakdown
   - Query refinement in action
4. Experiment with parameters:
   - Cache size
   - Number of examples (k)
   - Max refinement attempts

## Troubleshooting

**Issue**: Import errors
- **Solution**: Make sure you're in the right directory and have all dependencies installed via `uv sync`

**Issue**: Database not found
- **Solution**: Run `create_nobel_api_graph.py` first to create the database

**Issue**: API key errors
- **Solution**: Set `OPENROUTER_API_KEY` in your `.env` file

## Questions?

Refer to `IMPLEMENTATION.md` for detailed documentation of each component.
