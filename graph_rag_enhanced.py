import marimo

__generated_with = "0.14.17"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        rf"""
    # Enhanced Graph RAG using Text2Cypher

    This is an enhanced demo app in marimo with the following improvements:
    
    **Task 1: Text2Cypher Improvements**
    - Dynamic few-shot exemplar selection based on similarity
    - Self-refinement loop with syntax validation (EXPLAIN)
    - Rule-based post-processor for query quality
    
    **Task 2: Caching & Performance**
    - LRU cache for Text2Cypher results
    - Granular performance benchmarking
    - Timing breakdown visualization

    > \- Powered by Kuzu, DSPy and marimo \-
    """
    )
    return


@app.cell
def _(mo):
    text_ui = mo.ui.text(value="Which scholars won prizes in Physics and were affiliated with University of Cambridge?", full_width=True)
    show_perf = mo.ui.checkbox(label="Show performance metrics", value=True)
    show_cache = mo.ui.checkbox(label="Show cache statistics", value=True)
    return (text_ui, show_perf, show_cache)


@app.cell
def _(text_ui, show_perf, show_cache, mo):
    mo.vstack([text_ui, mo.hstack([show_perf, show_cache])])
    return


@app.cell
def _(
    KuzuDatabaseManager,
    EnhancedGraphRAG,
    mo,
    text_ui,
    example_retriever,
    example_map,
):
    db_name = "nobel.kuzu"
    db_manager = KuzuDatabaseManager(db_name)

    rag = EnhancedGraphRAG(
        retriever_model=example_retriever,
        example_map=example_map,
        db_manager=db_manager,
        cache_size=100,
        enable_performance_tracking=True,
    )

    question = text_ui.value

    with mo.status.spinner(title="Generating answer...") as _spinner:
        result = rag(db_manager=db_manager, question=question)

    query = result['query']
    answer = result['answer'].response
    was_cached = result.get('cached', False)
    
    perf_breakdown = rag.performance_tracker.get_timing_breakdown()
    print(perf_breakdown)

    cache_stats = rag.cache.get_stats()
    print(cache_stats)

    return answer, query, rag, was_cached, perf_breakdown, cache_stats

@app.cell
def _(mo, answer, query, was_cached, perf_breakdown, cache_stats):
    cache_indicator = "🔵 (cached)" if was_cached else "🟢 (not cached)"
    
    mo.vstack([
        mo.md(f"""### Query {cache_indicator}\n```cypher\n{query}\n```"""),
        mo.md(f"""### Answer\n{answer}"""),
        mo.md(f"""
            ### Cache Statistics
            - Size: {cache_stats['size']}/{cache_stats['max_size']}
            - Hits: {cache_stats['hits']}
            - Misses: {cache_stats['misses']}
            - Hit Rate: {cache_stats['hit_rate']:.1%}
            """)
    ])
    return


@app.cell
def _(perf_breakdown, create_text_visualization, mo):
    result = None
    if perf_breakdown:
        viz = create_text_visualization(perf_breakdown)
        result = mo.md(f"""### Performance Metrics\n```\n{viz}\n```""")
    return result


@app.cell
def _(dspy, json):
    from sentence_transformers import SentenceTransformer

    
    with open('examples/text2cypher_examples.json', 'r') as f:
        examples_from_json = json.load(f)

    cypher_examples = []
    for item in examples_from_json:
        example = dspy.Example(
            question=item['question'], 
            query=item['cypher']
        ).with_inputs('question') 
        cypher_examples.append(example)


    # Get questions from examples
    questions = []
    for example in cypher_examples:
        questions.append(example.question)


    st_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # Define a simple in-memory retriever
    class Embeddings(dspy.Module):
        def __init__(self, corpus, embedder, k=3):
            super().__init__()
            self.corpus = corpus
            self.embedder = embedder
            self.k = k
            self.corpus_embeddings = self.embedder(self.corpus)

        def forward(self, query: str, k: int = None):
            k = k if k is not None else self.k
            query_embedding = self.embedder(query)
            
            from sentence_transformers import util
            hits = util.semantic_search(query_embedding, self.corpus_embeddings, top_k=k)
            
            return [self.corpus[hit['corpus_id']] for hit in hits[0]]

    retriever_model = Embeddings(
        corpus=questions,
        embedder=st_model.encode,
        k=3
    )   
    
    def setup_example_retriever(examples, model):
        example_map = {ex.question: ex for ex in examples}
        return model, example_map
    
    example_retriever, example_map = setup_example_retriever(
        cypher_examples, retriever_model
    )
    
    print(f"Loaded and indexed {len(cypher_examples)} examples.")
    
    return (
        example_retriever,
        example_map,
        retriever_model
    )


@app.cell
def _(GraphSchema, Query, dspy):
    class PruneSchema(dspy.Signature):
        """
        Understand the given labelled property graph schema and the given user question. Your task
        is to return ONLY the subset of the schema (node labels, edge labels and properties) that is
        relevant to the question.
            - The schema is a list of nodes and edges in a property graph.
            - The nodes are the entities in the graph.
            - The edges are the relationships between the nodes.
            - Properties of nodes and edges are their attributes, which helps answer the question.
        """

        question: str = dspy.InputField()
        input_schema: str = dspy.InputField()
        pruned_schema: GraphSchema = dspy.OutputField()


    class Text2Cypher(dspy.Signature):
        """
        Translate the question into a valid Cypher query that respects the graph schema.

        <SYNTAX>
        - When matching on Scholar names, ALWAYS match on the `knownName` property
        - For countries, cities, continents and institutions, you can match on the `name` property
        - Use short, concise alphanumeric strings as names of variable bindings (e.g., `a1`, `r1`, etc.)
        - Always strive to respect the relationship direction (FROM/TO) using the schema information.
        - When comparing string properties, ALWAYS do the following:
            - Lowercase the property values before comparison using lower()
            - Use the WHERE clause
            - Use the CONTAINS operator to check for presence of one substring in the other
        - DO NOT use APOC as the database does not support it.
        </SYNTAX>

        <RETURN_RESULTS>
        - If the result is an integer, return it as an integer (not a string).
        - When returning results, return property values rather than the entire node or relationship.
        - Do not attempt to coerce data types to number formats (e.g., integer, float) in your results.
        - NO Cypher keywords should be returned by your query.
        </RETURN_RESULTS>
        """

        question: str = dspy.InputField()
        input_schema: str = dspy.InputField()
        query: Query = dspy.OutputField()


    class AnswerQuestion(dspy.Signature):
        """
        - Use the provided question, the generated Cypher query and the context to answer the question.
        - If the context is empty, state that you don't have enough information to answer the question.
        - When dealing with dates, mention the month in full.
        """

        question: str = dspy.InputField()
        cypher_query: str = dspy.InputField()
        context: str = dspy.InputField()
        response: str = dspy.OutputField()
    return AnswerQuestion, PruneSchema, Text2Cypher


@app.cell
def _(BAMLAdapter, OPENROUTER_API_KEY, dspy):
    lm = dspy.LM(
        model="openrouter/google/gemini-2.0-flash-001",
        api_base="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    try:
        dspy.configure(lm=lm, adapter=BAMLAdapter())
    except RuntimeError:
        # Ignore if already configured by another thread
        pass
    return


@app.cell
def _(kuzu):
    class KuzuDatabaseManager:
        """Manages Kuzu database connection and schema retrieval."""

        def __init__(self, db_path: str = "ldbc_1.kuzu"):
            self.db_path = db_path
            self.db = kuzu.Database(db_path, read_only=True)
            self.conn = kuzu.Connection(self.db)

        @property
        def get_schema_dict(self) -> dict[str, list[dict]]:
            response = self.conn.execute("CALL SHOW_TABLES() WHERE type = 'NODE' RETURN *;")
            nodes = [row[1] for row in response]    
            response = self.conn.execute("CALL SHOW_TABLES() WHERE type = 'REL' RETURN *;")
            rel_tables = [row[1] for row in response] 
            relationships = []
            for tbl_name in rel_tables:
                response = self.conn.execute(f"CALL SHOW_CONNECTION('{tbl_name}') RETURN *;")
                for row in response:
                    relationships.append({"name": tbl_name, "from": row[0], "to": row[1]})
            schema = {"nodes": [], "edges": []}

            for node in nodes:
                node_schema = {"label": node, "properties": []}
                node_properties = self.conn.execute(f"CALL TABLE_INFO('{node}') RETURN *;")
                for row in node_properties: 
                    node_schema["properties"].append({"name": row[1], "type": row[2]}) 
                schema["nodes"].append(node_schema)

            for rel in relationships:
                edge = {
                    "label": rel["name"],
                    "from": rel["from"],
                    "to": rel["to"],
                    "properties": [],
                }
                rel_properties = self.conn.execute(f"""CALL TABLE_INFO('{rel["name"]}') RETURN *;""")
                for row in rel_properties:      
                    edge["properties"].append({"name": row[1], "type": row[2]}) 
                schema["edges"].append(edge)
            return schema
    return (KuzuDatabaseManager,)


@app.cell
def _(BaseModel, Field):
    class Query(BaseModel):
        query: str = Field(description="Valid Cypher query with no newlines")


    class Property(BaseModel):
        name: str
        type: str = Field(description="Data type of the property")


    class Node(BaseModel):
        label: str
        properties: list[Property] | None


    class Edge(BaseModel):
        model_config = {"populate_by_name": True}
        label: str = Field(description="Relationship label")
        from_: Node = Field(alias="from", description="Source node label")
        to: Node = Field(description="Target node label")
        properties: list[Property] | None


    class GraphSchema(BaseModel):
        nodes: list[Node]
        edges: list[Edge]
    return GraphSchema, Query


@app.cell
def _(
    AnswerQuestion,
    Any,
    KuzuDatabaseManager,
    PruneSchema,
    Query,
    Text2Cypher,
    dspy,
    Text2CypherCache,
    CypherQueryValidator,
    CypherSelfRefinement,
    PerformanceTracker,
):
    class EnhancedGraphRAG(dspy.Module):
        """
        Enhanced DSPy module with caching, validation, and performance tracking.
        """

        def __init__(
            self, 
            retriever_model, 
            example_map, 
            db_manager: KuzuDatabaseManager,
            cache_size: int = 100,
            enable_performance_tracking: bool = True,
        ):
            super().__init__()
            self.prune = dspy.Predict(PruneSchema)
            self.text2cypher = dspy.ChainOfThought(Text2Cypher)
            self.generate_answer = dspy.ChainOfThought(AnswerQuestion)

            self.retriever_model = retriever_model
            self.example_map = example_map
            
            # Enhanced features
            self.cache = Text2CypherCache(max_size=cache_size)
            self.validator = CypherQueryValidator(db_manager.conn)
            self.self_refinement = CypherSelfRefinement(self.validator, max_attempts=3)
            self.performance_tracker = PerformanceTracker() if enable_performance_tracking else None
        
        def get_dynamic_examples(self, question: str, k: int = 3):
            """Retrieves k-most similar examples to the question."""
            retrieved_questions = self.retriever_model(question, k=k)
            
            dynamic_examples = [self.example_map[q] for q in retrieved_questions]
            return dynamic_examples

        def forward(self, db_manager: KuzuDatabaseManager, question: str):
            if self.performance_tracker:
                self.performance_tracker.current_run.clear()
            
            with self._track_stage("1_schema_retrieval"):
                input_schema = str(db_manager.get_schema_dict)
                schema_dict = db_manager.get_schema_dict

            with self._track_stage("2_cache_lookup"):
                cached_result = self.cache.get(question, schema_dict)
                if cached_result:
                    cached_result['cached'] = True
                    return cached_result

            with self._track_stage("3_schema_pruning"):
                prune_result = self.prune(question=question, input_schema=input_schema)
                schema = prune_result.pruned_schema

            with self._track_stage("4_example_retrieval"):
                dynamic_examples = self.get_dynamic_examples(question, k=3)

            with self._track_stage("5_text2cypher_generation"):
                text2cypher_result = self.text2cypher(
                    question=question,
                    input_schema=schema,
                    demos=dynamic_examples 
                )
                cypher_query = text2cypher_result.query.query

            with self._track_stage("6_query_validation_refinement"):
                refined_query, is_valid, error_history = self.self_refinement.refine(cypher_query)
                if not is_valid:
                    print(f"Warning: Query validation failed after refinement. Errors: {error_history}")
                cypher_query = refined_query

            with self._track_stage("7_query_execution"):
                try:
                    result = db_manager.conn.execute(cypher_query)
                    final_context = [item for row in result for item in row]
                    if not final_context:
                        final_context = "No results found in the database."
                except RuntimeError as e:
                    print(f"Error running query: {e}")
                    final_context = f"Database execution error: {e}"
            
            with self._track_stage("8_answer_generation"):
                print(f"DEBUG: Final Context: {final_context}")
                answer = self.generate_answer(
                    question=question,
                    cypher_query=cypher_query,
                    context=str(final_context)
                )
                print(f"DEBUG: Generated Answer: {answer}")
            
            response = {
                "question": question,
                "query": cypher_query,
                "answer": answer,
                "cached": False,
            }
            
            with self._track_stage("9_cache_storage"):
                self.cache.set(question, schema_dict, response)
            
            return response
        
        def _track_stage(self, stage_name: str):
            """Helper to conditionally track performance."""
            if self.performance_tracker:
                return self.performance_tracker.track_stage(stage_name)
            else:
                from contextlib import nullcontext
                return nullcontext()

    return (EnhancedGraphRAG,)


@app.cell
def _():
    return


@app.cell
def _():
    import marimo as mo
    import os
    from textwrap import dedent
    from typing import Any

    import dspy
    import kuzu
    from dotenv import load_dotenv
    from dspy.adapters.baml_adapter import BAMLAdapter

    from dspy.adapters.baml_adapter import BAMLAdapter

    from pydantic import BaseModel, Field

    import json
    
    from text2cypher_cache import Text2CypherCache
    from cypher_validator import CypherQueryValidator, CypherSelfRefinement
    from performance_benchmark import PerformanceTracker, create_text_visualization

    load_dotenv()

    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    return (
        Any,
        BAMLAdapter,
        BaseModel,
        Field,
        OPENROUTER_API_KEY,
        dspy,
        kuzu,
        mo,
        json,
        Text2CypherCache,
        CypherQueryValidator,
        CypherSelfRefinement,
        PerformanceTracker,
        create_text_visualization,
    )


if __name__ == "__main__":
    app.run()
