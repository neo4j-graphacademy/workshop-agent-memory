# Tests the environment: the .env file, the OpenAI and Neo4j connections, and
# that neo4j-agent-memory is installed.
# Run with: python test_environment.py
import os
import unittest

from dotenv import load_dotenv, find_dotenv
load_dotenv()


class TestEnvironment(unittest.TestCase):

    skip_env_variable_tests = True
    skip_openai_test = True
    skip_neo4j_test = True

    def test_env_file_exists(self):
        env_file_exists = True if find_dotenv() > "" else False
        if env_file_exists:
            TestEnvironment.skip_env_variable_tests = False
        self.assertTrue(env_file_exists, ".env file not found.")

    def env_variable_exists(self, variable_name):
        self.assertIsNotNone(
            os.getenv(variable_name),
            f"{variable_name} not found in .env file")

    def test_openai_variables(self):
        if TestEnvironment.skip_env_variable_tests:
            self.skipTest("Skipping OpenAI env variable test")

        self.env_variable_exists('OPENAI_API_KEY')
        self.assertIsNotNone(
            os.getenv('OPENAI_BASE_URL'),
            "OPENAI_BASE_URL not found in .env file - without it your workshop key is sent to OpenAI and rejected.")
        TestEnvironment.skip_openai_test = False

    def test_neo4j_variables(self):
        if TestEnvironment.skip_env_variable_tests:
            self.skipTest("Skipping Neo4j env variables test")

        self.env_variable_exists('NEO4J_URI')
        self.env_variable_exists('NEO4J_USERNAME')
        self.env_variable_exists('NEO4J_PASSWORD')
        TestEnvironment.skip_neo4j_test = False

    def test_memory_workspace_variables(self):
        if TestEnvironment.skip_env_variable_tests:
            self.skipTest("Skipping shared instance env variables test")

        self.assertIsNotNone(
            os.getenv('MVP_NEO4J_URI'),
            "MVP_NEO4J_URI not found in .env file - your instructor provides the shared instance values.")
        self.assertIsNotNone(
            os.getenv('MVP_NEO4J_USERNAME'),
            "MVP_NEO4J_USERNAME not found in .env file - your instructor provides the shared instance values.")
        self.assertIsNotNone(
            os.getenv('MVP_NEO4J_PASSWORD'),
            "MVP_NEO4J_PASSWORD not found in .env file - your instructor provides the shared instance values.")
        self.assertIsNotNone(
            os.getenv('MVP_SESSION_ID'),
            "MVP_SESSION_ID not found in .env file - set it to your name.")

    def test_openai_connection(self):
        if TestEnvironment.skip_openai_test:
            self.skipTest("Skipping OpenAI test")

        from openai import OpenAI

        msg = ""
        llm = OpenAI()

        # The workshop proxy serves chat completions and embeddings, but not
        # /models - so check the connection with the model the agent uses.
        try:
            response = llm.chat.completions.create(
                model="gpt-5.2",
                messages=[{"role": "user", "content": "ping"}],
                max_completion_tokens=16,
            )
        except Exception as error:
            response = None
            # The proxy explains itself - an idle session, for example, needs
            # reactivating rather than a new key. Show its message, not ours.
            detail = getattr(getattr(error, "body", None), "get", lambda _k: None)("message")
            msg = detail or (
                f"OpenAI connection failed ({type(error).__name__}). Check the "
                "OPENAI_API_KEY and OPENAI_BASE_URL values in .env file.")
        self.assertIsNotNone(response, msg)

    def test_neo4j_connection(self):

        msg = "Neo4j connection failed. Check the NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD values in .env file."
        connected = False

        if TestEnvironment.skip_neo4j_test:
            self.skipTest("Skipping Neo4j connection test")

        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USERNAME'),
                  os.getenv('NEO4J_PASSWORD'))
        )
        try:
            driver.verify_connectivity()
            try:
                driver.execute_query("RETURN true", database_=os.getenv('NEO4J_DATABASE'))
                connected = True
            except Exception:
                msg = "Neo4j database query failed. Check the NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD values in .env file."
        except Exception:
            msg = "Neo4j verify connection failed. Check the NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD values in .env file."

        driver.close()

        self.assertTrue(connected, msg)

    def test_agent_memory_installed(self):
        try:
            import neo4j_agent_memory  # noqa: F401
            installed = True
        except ImportError:
            installed = False
        self.assertTrue(
            installed,
            "neo4j-agent-memory not installed. Run: pip install \"neo4j-agent-memory[openai,pydantic-ai]\"")

    def test_memory_workspace_connection(self):
        if TestEnvironment.skip_env_variable_tests or not os.getenv('MVP_NEO4J_URI'):
            self.skipTest("Skipping shared instance connection test")

        from neo4j import GraphDatabase

        msg = ""
        try:
            driver = GraphDatabase.driver(
                os.getenv('MVP_NEO4J_URI'),
                auth=(os.getenv('MVP_NEO4J_USERNAME'),
                      os.getenv('MVP_NEO4J_PASSWORD'))
            )
            driver.verify_connectivity()
            driver.close()
            connected = True
        except Exception as error:
            connected = False
            msg = (f"Shared instance connection failed ({error}). "
                   "Check the MVP_NEO4J_* values in .env file.")
        self.assertTrue(connected, msg)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestEnvironment('test_env_file_exists'))
    suite.addTest(TestEnvironment('test_openai_variables'))
    suite.addTest(TestEnvironment('test_neo4j_variables'))
    suite.addTest(TestEnvironment('test_memory_workspace_variables'))
    suite.addTest(TestEnvironment('test_openai_connection'))
    suite.addTest(TestEnvironment('test_neo4j_connection'))
    suite.addTest(TestEnvironment('test_agent_memory_installed'))
    suite.addTest(TestEnvironment('test_memory_workspace_connection'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
