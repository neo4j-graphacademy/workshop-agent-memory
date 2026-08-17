# Seeds fake "other attendee" messages for a demo/video recording of
# find_similar_attendees. That tool matches on short-term Message content from
# OTHER sessions (memory_agent_mvp.py: find_similar_attendees), so plain
# Person nodes are invisible to it - this goes through the real
# neo4j_agent_memory API so the messages get proper embeddings.
#
# Marked with metadata={"temporary": True, "demo_batch": ...} for cleanup.
# Run with: python add_temp_attendees.py
#
# To remove afterwards (run against MVP_NEO4J_* - see cleanup snippet printed
# at the end).

import asyncio
import os

from dotenv import load_dotenv

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config import EmbeddingConfig, Neo4jConfig

load_dotenv()

BATCH_ID = "video-demo-3"

# One "self-introduction" message per attendee, in the same shape as the
# real learner's: role + company + why they're at an agent-memory workshop +
# a couple of unrelated personal interests. Gives find_similar_attendees
# something plausible to match on for both professional and personal queries.
ATTENDEES = [
    ("attendee-derek-pemberton", "Derek Pemberton",
     "Hey, I'm Derek. I work as a backend engineer at a fintech, building a fraud-detection agent that needs to remember past flagged patterns instead of re-deriving them every session. Outside of work I've a grand interest in vintage synthesizers and canal boats."),
    ("attendee-nadia-okonkwo", "Nadia Okonkwo",
     "Hi, I'm Nadia, a data scientist at a pharma company. I'm here to figure out how to give our clinical-trial assistant durable memory of prior patient cohorts instead of re-reading the same documents every query. I'm big into amateur radio and birdwatching in my spare time."),
    ("attendee-colin-bracewell", "Colin Bracewell",
     "I'm Colin, a machine learning engineer at a logistics company. We're prototyping a route-planning agent and I want it to remember which depots have caused problems before. Outside work I do dry-stone walling and sing in a local choir."),
    ("attendee-priya-balakrishnan", "Priya Balakrishnan",
     "Hey all, Priya here - I'm a software engineer at an ed-tech startup building a tutoring chatbot. This workshop is exactly what I need for giving it long-term memory of each student. I'm also really into calligraphy and correspondence chess."),
    ("attendee-terrence-whitfield", "Terrence Whitfield",
     "I'm Terrence, a solutions architect at a bank. We're building a customer-service agent and keep hitting the same problem - no memory across sessions - so I'm here for the neo4j-agent-memory package specifically. For fun I collect and restore old typewriters."),
    ("attendee-ingrid-halvorsen", "Ingrid Halvorsen",
     "Hi, I'm Ingrid, a security engineer at a healthcare SaaS company. I'm mainly interested in the RBAC and property-level access control side of agent memory, since our agents will be handling patient data. I also do cold-water swimming and marquetry."),
    ("attendee-marcus-delacroix", "Marcus Delacroix",
     "I'm Marcus, a developer relations engineer at a dev-tools company. I'm here to properly understand GraphRAG and agent memory so I can write better docs and examples for our users. Away from the keyboard I play in a brass band and grow dahlias."),
    ("attendee-sheila-nkrumah", "Sheila Nkrumah",
     "Hey, I'm Sheila, a PhD student researching multi-agent systems. I'm hoping the entity resolution and reasoning-trace parts of this workshop feed directly into my thesis. Outside of research I do fell running and medieval reenactment."),
    ("attendee-bartholomew-sykes", "Bartholomew Sykes",
     "I'm Bartholomew, a site reliability engineer at a cloud provider. I keep getting paged for LLM agents behaving unpredictably, so I'm here to understand how memory and reasoning traces can make them more debuggable. I restore vintage motorcycles and home-brew beer in my spare time."),
    ("attendee-aisling-doyle", "Aisling Doyle",
     "Hi, I'm Aisling, a bioinformatics researcher at a university. I want an agent that remembers the protein-interaction queries I've already run instead of me re-explaining context every session. I collect vintage cameras and I'm learning bell ringing."),
    ("attendee-reuben-achterberg", "Reuben Achterberg",
     "I'm Reuben, a platform engineer at a retailer. We're building a recommendation agent and want it to remember a shopper's stated preferences long-term, not just within a session. Outside of work I do letterpress printing and long-distance cycling."),
    ("attendee-constance-whitmore", "Constance Whitmore",
     "Hey, I'm Constance, a QA specialist in pharma compliance. I'm exploring whether an agent with memory could track compliance decisions and the reasoning behind them over time. I also do stained glass work and play competitive bridge."),
    ("attendee-faruk-demirci", "Faruk Demirci",
     "I'm Faruk, a full-stack developer at a nonprofit. I'm building a caseworker assistant that needs to remember details about each case across many conversations without re-reading every file. For fun I forage for wild mushrooms and do folk dancing."),
    ("attendee-osei-boateng", "Osei Boateng",
     "Hi, I'm Osei, a data engineer at an energy company. I'm here for the knowledge-graph side - we're building an outage-response agent that needs to recall past grid incidents. Outside of work I restore vinyl records and play chess."),
    ("attendee-rosalind-hepplewhite", "Rosalind Hepplewhite",
     "I'm Rosalind, an engineering manager at an insurance company. My team's building a claims-handling agent and I want to understand memory architecture well enough to review their design properly. I sing in a choir and I'm slowly restoring a narrowboat."),
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
