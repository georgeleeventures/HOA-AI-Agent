"""Mock heavy dependencies for unit testing without Vertex AI / full asyncpg."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

# Must be done before any app imports
_mocks = {}

for mod_name in [
    "vertexai",
    "vertexai.generative_models",
    "vertexai.language_models",
    "asyncpg",
    "pgvector",
    "pgvector.asyncpg",
    "google.oauth2.credentials",
    "google.oauth2",
    "google.genai",
    "google.genai.types",
    "google",
    "googleapiclient",
    "googleapiclient.discovery",
]:
    if mod_name not in sys.modules:
        mock = MagicMock()
        sys.modules[mod_name] = mock
        _mocks[mod_name] = mock

# Ensure asyncpg.Pool exists as a type
sys.modules["asyncpg"].Pool = type("Pool", (), {})
