# Adds a batch of fake Person nodes for a demo/video recording.
# Marked with `temporary: true` and a `demo_batch` timestamp-free id so they're
# easy to find and remove afterwards. Run with: python add_temp_people.py
# To remove them again: MATCH (p:Person {temporary: true}) DETACH DELETE p

import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
BATCH_ID = "video-demo-1"

PEOPLE = [
    {"name": "Derek Pemberton", "occupation": "Electrician", "city": "Leeds"},
    {"name": "Nadia Okonkwo", "occupation": "Pharmacist", "city": "Bristol"},
    {"name": "Colin Bracewell", "occupation": "Bus Driver", "city": "Glasgow"},
    {"name": "Priya Balakrishnan", "occupation": "Civil Engineer", "city": "Coventry"},
    {"name": "Terrence Whitfield", "occupation": "Butcher", "city": "Sheffield"},
    {"name": "Ingrid Halvorsen", "occupation": "Marine Biologist", "city": "Aberdeen"},
    {"name": "Marcus Delacroix", "occupation": "Sommelier", "city": "Bath"},
    {"name": "Sheila Nkrumah", "occupation": "Midwife", "city": "Manchester"},
    {"name": "Bartholomew Sykes", "occupation": "Locksmith", "city": "Norwich"},
    {"name": "Aisling Doyle", "occupation": "Radiographer", "city": "Belfast"},
    {"name": "Reuben Achterberg", "occupation": "Beekeeper", "city": "York"},
    {"name": "Constance Whitmore", "occupation": "Actuary", "city": "Edinburgh"},
    {"name": "Faruk Demirci", "occupation": "Upholsterer", "city": "Cardiff"},
    {"name": "Winifred Applegate", "occupation": "Librarian", "city": "Oxford"},
    {"name": "Osei Boateng", "occupation": "Quantity Surveyor", "city": "Liverpool"},
    {"name": "Rosalind Hepplewhite", "occupation": "Optometrist", "city": "Durham"},
    {"name": "Vincent Kowalczyk", "occupation": "Roofer", "city": "Plymouth"},
    {"name": "Beatrice Alderton", "occupation": "Chartered Accountant", "city": "Exeter"},
    {"name": "Girish Chandrasekaran", "occupation": "Orthodontist", "city": "Nottingham"},
    {"name": "Hollis Tremblay", "occupation": "Ferry Captain", "city": "Portsmouth"},
    {"name": "Marjorie Ffoulkes", "occupation": "Antiques Dealer", "city": "Canterbury"},
    {"name": "Dov Rosenzweig", "occupation": "Structural Engineer", "city": "Leicester"},
    {"name": "Peregrine Ashworth", "occupation": "Vet", "city": "Chester"},
    {"name": "Chidinma Eze", "occupation": "Air Traffic Controller", "city": "Southampton"},
    {"name": "Lachlan Fergusson", "occupation": "Cooper", "city": "Inverness"},
]


def main():
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    driver.verify_connectivity()

    driver.execute_query(
        """
        UNWIND $rows AS row
        CREATE (p:Person {
            name: row.name,
            occupation: row.occupation,
            city: row.city,
            temporary: true,
            demo_batch: $batch_id
        })
        """,
        rows=PEOPLE,
        batch_id=BATCH_ID,
        database_=DATABASE,
    )
    print(f"Created {len(PEOPLE)} temporary Person nodes (demo_batch='{BATCH_ID}').")
    print("To remove them later:")
    print("  MATCH (p:Person {temporary: true}) DETACH DELETE p")

    driver.close()


if __name__ == "__main__":
    main()
