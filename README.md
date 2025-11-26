# Enhancing LLM Inference with GraphRAG

A production-ready GraphRAG (Graph Retrieval-Augmented Generation) system that combines DSPy, Kuzu graph database, and LLMs to answer natural language questions over structured knowledge graphs.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-2.0+-green.svg)](https://dspy.ai/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 Overview

This project implements an enhanced Text2Cypher pipeline that translates natural language questions into Cypher queries, executes them on a Kuzu graph database, and generates accurate, grounded answers using LLMs.

### Key Features

- ✨ **Dynamic Few-Shot Learning**: Semantic similarity-based example selection using SentenceTransformers
- 🎯 **Automated Schema Pruning**: Reduces context size by selecting only relevant graph schema
- ✅ **Query Validation**: Self-refinement loop with EXPLAIN-based validation (up to 3 attempts)
- ⚡ **Intelligent Caching**: LRU cache for query results with SHA-256 hashing
- 📊 **Performance Profiling**: Granular timing instrumentation across 9 pipeline stages
- 🔧 **Rule-based Post-Processing**: Enforces query correctness (lowercasing, CONTAINS usage)
- 📱 **Interactive UI**: Marimo-based notebook interface with real-time visualization

## ✨ Demo
<img width="1918" height="991" alt="image" src="https://github.com/user-attachments/assets/a5e10de4-de16-4333-a1e1-18f66d634a15" />
<img width="1914" height="975" alt="image" src="https://github.com/user-attachments/assets/a0b0a08f-f3c9-4cad-8ca1-68f124b058cf" />


## 📁 Project Structure

```
Enhancing-LLM-Inference-with-GraphRAG/
├── 📄 graph_rag_enhanced.py          # Main enhanced GraphRAG application (marimo)
├── 📄 graph_rag.py                   # Basic GraphRAG demo (marimo)
├── 📄 demo_workflow.py               # Step-by-step workflow demonstration (marimo)
├── 📄 create_nobel_api_graph.py      # Database creation script (marimo)
├── 📄 eda.py                         # Exploratory data analysis (marimo)
│
├── 📁 utils/                         # Core utility modules
│   ├── text2cypher_cache.py         # LRU cache implementation
│   ├── cypher_validator.py          # Query validation & self-refinement
│   └── performance_benchmark.py     # Performance tracking & visualization
│
├── 📁 examples/                      # Training data
│   └── text2cypher_examples.json    # Few-shot examples for query generation
│
├── 📁 data/                          # Raw data
│   └── nobel.json                   # Nobel Prize dataset
│
├── 📁 docs/                          # Documentation
│   ├── report.tex                   # Technical report (LaTeX)
│   └── IMPLEMENTATION.md            # Implementation details
│
├── 📄 nobel.kuzu                     # Kuzu graph database (41MB)
├── 📄 pyproject.toml                 # Project dependencies
├── 📄 .env                           # API keys (not in repo)
└── 📄 README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- OpenRouter API key (for Gemini 2.0 Flash)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/alexha11/Enhancing-LLM-Inference-with-GraphRAG.git
cd Enhancing-LLM-Inference-with-GraphRAG
```

2. **Create a virtual environment**
```bash
python -m venv .venv
```

3. **Activate the virtual environment**
```bash
# On Windows
.venv\Scripts\activate

# On Linux/Mac
source .venv/bin/activate
```

4. **Install dependencies**
```bash
# Using uv (recommended)
uv sync
```

5. **Set up environment variables**

Create a `.env` file in the project root:
```bash
OPENROUTER_API_KEY=your_api_key_here
```

Get your API key from [OpenRouter](https://openrouter.ai/).

6. **Create the graph database** (if not already present)
```bash
uv run create_nobel_api_graph.py
```

This will create `nobel.kuzu` with 726 scholars, 399 prizes, and their relationships.

### Running the Application

#### Option 1: Enhanced GraphRAG App (Recommended)

Run the full-featured GraphRAG system with caching, validation, and performance tracking:

```bash
uv run marimo run graph_rag_enhanced.py
```

Then open your browser to the displayed URL (typically http://127.0.0.1:2718).

#### Option 2: Edit Mode (Development)

For development and experimentation:

```bash
uv run marimo edit graph_rag_enhanced.py
```

This allows you to modify cells and see changes in real-time.

#### Option 3: Basic Demo

Run the simpler baseline GraphRAG without enhancements:

```bash
uv run marimo run graph_rag.py
```

## 🏗️ Architecture

### Pipeline Flow

```
User Query
    ↓
1. Schema Retrieval      (1% - 64ms)
    ↓
2. Cache Lookup          (<1% - <1ms)
    ↓ (cache miss)
3. Schema Pruning        (52% - 3.4s) ← BOTTLENECK
    ↓
4. Example Retrieval     (1% - 33ms)
    ↓
5. Text2Cypher Gen       (23% - 1.5s)
    ↓
6. Query Validation      (1% - 27ms)
    ↓
7. Database Execution    (<1% - 10ms)
    ↓
8. Answer Generation     (22% - 1.5s)
    ↓
9. Cache Storage         (<1% - <1ms)
    ↓
Natural Language Answer
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM Framework** | DSPy 2.0+ | Declarative prompting & modules |
| **Language Model** | Gemini 2.0 Flash | Query generation & reasoning |
| **Graph Database** | Kuzu | Embedded graph storage |
| **Embeddings** | SentenceTransformers (MiniLM-L6-v2) | Semantic similarity |
| **Notebook UI** | Marimo | Interactive development |
| **API Gateway** | OpenRouter | LLM access |

## 📊 Database Schema

### Node Types
- **Scholar** (726 nodes): Nobel laureates with names, dates, affiliations
- **Prize**: Nobel prizes by year and category
- **Institution**: Universities and research institutions
- **City**: Birth/affiliation locations
- **Country**: Countries
- **Continent**: Continents

### Relationship Types
- `WON`: Scholar → Prize (with portion property)
- `AFFILIATED_WITH`: Scholar → Institution
- `BORN_IN`: Scholar → City
- `DIED_IN`: Scholar → City
- `IS_LOCATED_IN`: Institution → City
- `IS_CITY_IN`: City → Country
- `IS_COUNTRY_IN`: Country → Continent

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM access | Yes |

### System Parameters

Edit these in `graph_rag_enhanced.py`:

```python
# Cache size (default: 100)
cache_size = 100

# Maximum refinement attempts (default: 3)
max_attempts = 3

# Number of few-shot examples (default: 3)
k_examples = 3

# Enable performance tracking (default: True)
enable_performance_tracking = True
```

## 📈 Performance Metrics

### Typical Query Performance (First Run)

| Stage | Time | Percentage |
|-------|------|------------|
| Schema Pruning | 3.4s | 52% |
| Text2Cypher Generation | 1.5s | 23% |
| Answer Generation | 1.5s | 22% |
| Other Operations | 0.2s | 3% |
| **Total** | **6.6s** | **100%** |

### Cache Performance

- **Cache Hit**: ~10ms (650× speedup)
- **Cache Miss**: ~6.6s (full pipeline)
- **Hit Rate** (repeated queries): 100%

## 🧪 Example Queries

The system can answer questions like:

1. **Affiliation-based queries**:
   - "Which scholars won prizes in Physics and were affiliated with University of Cambridge?"
   
2. **Category-based queries**:
   - "List all scholars who won the Nobel Prize in Chemistry"
   
3. **Multi-hop reasoning**:
   - "Which countries have institutions affiliated with Medicine prize winners?"
   
4. **Temporal queries**:
   - "Who won physics prizes between 1950 and 1960?"

## 📝 Code Modules

### Core Application
- **`graph_rag_enhanced.py`**: Main application with all enhancements
- **`graph_rag.py`**: Baseline implementation for comparison
- **`demo_workflow.py`**: Educational step-by-step workflow

### Utility Modules

#### `utils/text2cypher_cache.py`
LRU cache for query results:
```python
cache = Text2CypherCache(max_size=100)
result = cache.get(question, schema)  # Returns cached result or None
cache.set(question, schema, result)   # Stores new result
stats = cache.get_stats()              # {hits, misses, hit_rate, ...}
```

#### `utils/cypher_validator.py`
Query validation and refinement:
```python
validator = CypherQueryValidator(conn)
is_valid, error = validator.validate(query)

refinement = CypherSelfRefinement(validator, max_attempts=3)
refined_query, is_valid, history = refinement.refine(query)
```

#### `utils/performance_benchmark.py`
Performance tracking:
```python
tracker = PerformanceTracker()
with tracker.track_stage("stage_name"):
    # code to measure
    
breakdown = tracker.get_timing_breakdown()
tracker.print_summary()
```

### Data Scripts
- **`create_nobel_api_graph.py`**: Creates Kuzu database from JSON
- **`eda.py`**: Exploratory data analysis notebook


## Learning Outcomes

Through this implementation, you gain hands-on experience with:

1. **Prompt Engineering**: Dynamic few-shot learning, structured prompts
2. **Iterative Query Generation**: Self-refinement loops, validation strategies
3. **Performance Optimization**: Caching strategies, profiling, bottleneck identification
4. **System Design**: Modular architecture, separation of concerns
5. **Production Readiness**: Error handling, monitoring, statistics tracking

## Future Enhancements

Potential improvements:
- More sophisticated repair strategies (e.g., LLM-based repair)
- Query result caching in addition to query caching
- Distributed caching (Redis)
- More detailed flamegraph visualization
- A/B testing framework for different prompt strategies
- Query optimization hints based on performance data


## 🐛 Troubleshooting

**1. "Module not found" errors**
```bash
# Ensure you're using the venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Or use uv run
uv run marimo edit graph_rag_enhanced.py
```

## 📚 Additional Resources

- [DSPy Documentation](https://dspy.ai/)
- [Kuzu Documentation](https://kuzudb.com/)
- [Marimo Documentation](https://docs.marimo.io/)
- [OpenRouter](https://openrouter.ai/)
- [Technical Report](docs/report.tex)

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

1. **Performance Optimization**: Reduce schema pruning latency
2. **Schema Caching**: Implement LRU cache for pruned schemas
3. **Parallel Execution**: Run independent stages concurrently
4. **Model Comparison**: Benchmark different LLMs
5. **Test Suite**: Comprehensive evaluation dataset

## 📄 License

MIT License - see LICENSE file for details.

Project developed as part of CS-E4780 - Scalable Systems and Data Management at Aalto University.

## 🙏 Acknowledgments

- DSPy team for the excellent framework
- Kuzu team for the embedded graph database
- Marimo team for reactive notebooks
- Nobel Prize API for the dataset

---

**Note**: This project uses the Gemini 2.0 Flash model via OpenRouter. API costs apply based on usage. See [OpenRouter pricing](https://openrouter.ai/docs/pricing) for details.
