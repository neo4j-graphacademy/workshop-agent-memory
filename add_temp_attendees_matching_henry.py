# Seeds a few fake attendees whose bios genuinely overlap with Henry's own
# introduction (curriculum development, Neo4j, agent-memory workshops,
# sundials, history) - close enough in wording to actually clear the 0.7
# cosine-similarity threshold search_messages() applies, unlike the broader
# video-demo-3 batch (add_temp_attendees.py), which is topically plausible
# but shares little vocabulary with Henry's specific interests.
#
# Marked with metadata={"temporary": True, "demo_batch": ...} for cleanup.
# Run with: python add_temp_attendees_matching_henry.py

import asyncio
import os

from dotenv import load_dotenv

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config import EmbeddingConfig, Neo4jConfig

load_dotenv()

BATCH_ID = "video-demo-4"

ATTENDEES = [
    ("attendee-clara-fenwick", "Clara Fenwick",
     "Hey, I'm Clara. I work as a curriculum developer at another edtech company, building internal workshops on neo4j-agent-memory to onboard our own engineers. I have a grand interest in sundials and antique clockwork - I collect old timepieces."),
    ("attendee-walter-pryce", "Walter Pryce",
     "Hi, I'm Walter, a digitisation lead at a museum. I'm building a Neo4j knowledge graph of historical artifacts and ancient astronomical instruments. I have a grand interest in history, particularly the history of timekeeping and sundials."),
    ("attendee-imogen-carraway", "Imogen Carraway",
     "I'm Imogen, a developer advocate who runs graph database workshops. I'm here exploring neo4j-agent-memory for my own training material. I have a grand interest in history and antique sundials - I even built one for my garden."),
    ("attendee-desmond-okafor", "Desmond Okafor",
     "Hey, I'm Desmond. I used to be an archivist, now I'm a data engineer building an agent memory system for a national archive's historical records. I have a grand interest in ancient history and old scientific instruments like sundials and astrolabes."),
    ("attendee-fenella-marsh", "Fenella Marsh",
     "Hi, I'm Fenella, an instructional designer writing curriculum for internal LLM agent training at my company. I have a grand interest in history, and I restore old sundials as a hobby."),
]


async def main():
    settings = MemorySettings(
        neo4j=Neo4jConfig(
            uri=os.environ["MVP_NEO4J_URI"],
            username=os.environ["MVP_NEO4J_USERNAME"],
            password=os.environ["MVP_NEO4J_PASSWORD"],
        ),
        embedding=EmbeddingConfig(api_key=os.environ["OPENAI_API_KEY"]),
    )

    async with MemoryClient(settings) as memory:
        for session_id, name, content in ATTENDEES:
            await memory.short_term.add_message(
                session_id, "user", content,
                user_identifier=session_id,
                extract_entities=False,
                extract_relations=False,
                generate_embedding=True,
                metadata={"temporary": True, "demo_batch": BATCH_ID, "fake_name": name},
            )
            print(f"Added: {name} ({session_id})")

    print(f"\nSeeded {len(ATTENDEES)} fake attendee messages (demo_batch='{BATCH_ID}').")
    print("To remove them later, run against the MVP_NEO4J_* instance:")
    print(
        f"  MATCH (m:Message) WHERE m.metadata CONTAINS '\"demo_batch\": \"{BATCH_ID}\"'\n"
        "  OPTIONAL MATCH (c:Conversation)-[:HAS_MESSAGE]->(m)\n"
        "  DETACH DELETE m, c"
    )


if __name__ == "__main__":
    asyncio.run(main())
