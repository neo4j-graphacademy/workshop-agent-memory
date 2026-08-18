# agent.py - the agent you build up through the workshop.
#
# It starts as a copy of agent_no_memory.py: the three-tool GraphRAG agent, no
# memory. Follow the lessons and fill in the marked sections, one memory layer
# at a time, until this file matches memory_agent_mvp.py.

import asyncio
import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from neo4j import GraphDatabase
from pydantic_ai import Agent, RunContext

from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever, VectorCypherRetriever

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config import (
    Neo4jConfig, EmbeddingConfig, ExtractionConfig, ExtractorType,
)

load_dotenv()

# --- Memory client (module 2, lesson 1): import MemoryClient, MemorySettings,
#     and the config objects here.

# Silence the driver's deprecation notices for the vector-index queries.
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
# Transient write conflicts retry automatically - don't print the retry.
logging.getLogger("neo4j.session").setLevel(logging.ERROR)

MODEL = "openai-chat:gpt-5.2"
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# --- Short-term memory (module 2, lesson 2): name the session and the user
#     here, for example  SESSION_ID = "learner"
SESSION_ID = "learner"
USER_ID = "learner"

# --- Short-term memory (module 2, lesson 2): define AgentDeps here,
#     above the knowledge-graph tools.

@dataclass
class AgentDeps:  # (1)
    memory_client: MemoryClient
    user_id: str
    session_id: str
    current_query: str | None = None

# --- Reasoning (module 4, lesson 1): define report_step here, above the
#     tools that call it.

# --- The agent's knowledge-graph tools (identical to agent_no_memory.py) ------

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
)
embedder = OpenAIEmbeddings(model="text-embedding-3-small")
llm = OpenAILLM(model_name="gpt-5.2")


def run_query(cypher, **params):
    """Run a Cypher query and return the rows as plain dicts."""
    records, _, _ = driver.execute_query(cypher, parameters_=params, database_=DATABASE)
    return [r.data() for r in records]


# GraphRAG retrieval (the genai workshop's canonical query): vector-match a
# passage, return its lesson, and traverse to the entities connected to it.
GRAPHRAG_RETRIEVAL = """
MATCH (node)-[:FROM_DOCUMENT]->(d)-[:PDF_OF]->(lesson)
RETURN
    node.text as text, score,
    lesson.url as lesson_url,
    collect {
        MATCH (node)<-[:FROM_CHUNK]-(entity)-[r]->(other)-[:FROM_CHUNK]->()
        WITH toStringList([
            [l IN labels(entity)
                WHERE NOT l IN ["__KGBuilder__", "__Entity__"]][0],
            entity.name,
            type(r),
            [l IN labels(other)
                WHERE NOT l IN ["__KGBuilder__", "__Entity__"]][0],
            other.name
            ]) as values
        RETURN reduce(acc = "", item in values | acc || coalesce(item || ' ', ''))
    } as associated_entities
"""
vector_retriever = VectorCypherRetriever(
    driver,
    index_name="chunkEmbedding",
    embedder=embedder,
    retrieval_query=GRAPHRAG_RETRIEVAL,
    neo4j_database=DATABASE,
)

# Natural language -> Cypher, with an example to steer query generation.
examples = [
    "USER INPUT: 'Find a node with the name $name?' QUERY: MATCH (node) WHERE toLower(node.name) CONTAINS toLower($name) RETURN node.name AS name, labels(node) AS labels",
]
text2cypher_retriever = Text2CypherRetriever(
    driver=driver, neo4j_database=DATABASE, llm=llm, examples=examples,
)


def get_schema() -> list:
    """Get the schema of the graph database - its node labels and relationship
    types. Use this first if you are unsure how the graph is structured."""
    return run_query("CALL db.schema.visualization()")


def search_lesson_content(query: str) -> list:
    """GraphRAG search over lesson content: semantically match passages and
    return each one together with the graph entities connected to it. Use for
    open-ended 'what does the material say about X' questions."""
    result = vector_retriever.search(query_text=query, top_k=5)
    return [item.content for item in result.items]


def query_database(query: str) -> list:
    """Answer a question by converting it to a Cypher query and running it. Use
    for specific, structured questions like 'how many lessons are there'."""
    result = text2cypher_retriever.search(query_text=query)
    return [item.content for item in result.items]


# --- Memory client (module 2, lesson 1): build memory_settings here.
#     memory_settings = MemorySettings(neo4j=..., embedding=..., extraction=...)
memory_settings = MemorySettings(
    neo4j=Neo4jConfig(  # (1)
        uri=os.environ["NEO4J_URI"],
        username=os.environ["NEO4J_USERNAME"],
        password=os.environ["NEO4J_PASSWORD"],
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    ),
    embedding=EmbeddingConfig(api_key=os.environ["OPENAI_API_KEY"]),  # (2)
    extraction=ExtractionConfig(extractor_type=ExtractorType.LLM),
    )

SYSTEM_PROMPT = (
    "You are an assistant for a Neo4j knowledge graph of course material. "
    "Answer questions about the material with get_schema, search_lesson_content, and query_database, and draw on what you remember to help."
    "When you conclude something durable about the learner or their work, record it with save_fact as a subject, predicate, and object. "
    "Save anything worth keeping."
)

agent = Agent(
    MODEL,
    deps_type=AgentDeps,
    tools=[get_schema, search_lesson_content, query_database],
    system_prompt=SYSTEM_PROMPT,
)

# --- Short-term memory (module 2, lesson 2): add your dynamic system prompt
#     here, below the agent, with @agent.system_prompt reading get_context on
#     every turn.
@agent.system_prompt  # (1)
async def what_you_remember(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.current_query is None:  # (2)
        return ""
    context = await ctx.deps.memory_client.get_context(  # (3)
        ctx.deps.current_query, session_id=ctx.deps.session_id,
    )
    return f"What you remember:\n{context}"

# --- Long-term memory (module 3, lesson 1): define your agent's four memory
#     tools here - search_messages, search_entities, save_preference,
#     and recall_preferences.

@agent.tool
async def search_messages(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search past conversation messages for relevant context."""
    messages = await ctx.deps.memory_client.short_term.search_messages(  # (1)
        query, session_id=ctx.deps.session_id, limit=5,
    )
    return "\n".join(f"[{m.role.value}] {m.content[:200]}" for m in messages) or "No matching messages."


@agent.tool
async def search_entities(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search the entities the agent knows about - the people, places, and
    things it has learned - by meaning."""
    entities = await ctx.deps.memory_client.long_term.search_entities(query, limit=10)  # (2)
    return "\n".join(f"{e.name} ({e.type})" for e in entities) or "No matching entities."


@agent.tool
async def save_preference(ctx: RunContext[AgentDeps], category: str, preference: str) -> str:
    """Save how the user likes to work, filed under a category."""
    await ctx.deps.memory_client.long_term.add_preference(  # (3)
        category=category, preference=preference, user_identifier=ctx.deps.user_id,
    )
    return f"Saved: {category} - {preference}"


@agent.tool
async def recall_preferences(ctx: RunContext[AgentDeps], topic: str) -> str:
    """Read back the user's preferences related to a topic."""
    prefs = await ctx.deps.memory_client.long_term.search_preferences(topic, limit=10)  # (4)
    return "\n".join(f"[{p.category}] {p.preference}" for p in prefs) or "No preferences on that yet."

# --- Long-term memory (module 3, lesson 5): define your save_fact
#     @agent.tool here.
@agent.tool
async def save_fact(ctx: RunContext[AgentDeps], subject: str, predicate: str, obj: str) -> str:
    """Record a durable fact about the learner or their work, as a
    subject, predicate, object triple."""
    await ctx.deps.memory_client.long_term.add_fact(
        subject=subject, predicate=predicate, obj=obj,
        metadata={"user_id": ctx.deps.user_id, "session_id": ctx.deps.session_id},
    )
    return f"Recorded: {subject} {predicate} {obj}."

# --- Reasoning (module 4, lesson 2): define how_did_i_handle here, below
#     save_fact.

# --- Your own tool (module 5): define your custom @agent.tool here.


async def main():
    # --- Memory client (module 2, lesson 1): open the MemoryClient around
    #     the body of main().
    async with MemoryClient(memory_settings) as memory:
        print("Agent ready. No memory yet - ask about the course material.")
        print("Type 'exit' (or Ctrl-D) to quit.\n")
        try:
            while True:
                try:
                    user_input = input("you> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not user_input or user_input.lower() in {"exit", "quit"}:
                    break

                # --- Short-term memory (module 2, lesson 2): store the user's
                #     message here.
                await memory.short_term.add_message(  # (1)
                SESSION_ID, "user", user_input, user_identifier=USER_ID,
                )

                # --- Reasoning (module 4, lesson 1): open the trace here, before
                #     the deps build - either ending closes it.

                # --- Short-term memory (module 2, lesson 2): build the turn's
                #     deps here.
                deps = AgentDeps(  # (2)
                    memory_client=memory,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    current_query=user_input,
                )

                result = await agent.run(user_input, deps=deps)  # (3)
                print(f"\nagent> {result.output}\n")

                # --- Short-term memory (module 2, lesson 2): store the agent's
                #     answer here, once it has printed.
                await memory.short_term.add_message(  # (4)
                    SESSION_ID, "assistant", str(result.output), user_identifier=USER_ID,
                )
        finally:
            driver.close()
        print("\nGoodbye.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
