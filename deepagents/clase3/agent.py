from langchain_openai import ChatOpenAI

# 1. Initialize the local LM Studio model
local_llm = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",  # Points to LM Studio
    api_key="lm-studio",                 # LM Studio doesn't require a real key, but a placeholder string prevents errors
    model="google/gemma-4-e2b",      # Match the name/identifier loaded in LM Studio
    temperature=0                       # Low temperature is critical for agent tool accuracy,
    )

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from pathlib import Path

# Importar api key desde las variables de entorno
from dotenv import load_dotenv
load_dotenv()

# importar tools (relative import for running from this directory)
from tools import (
    download_viirs_snpp_peru,
    fires_clean,
    download_ctry_shp,
    intersect_and_collapse_fires_peru,
    folium_choropleth_peru
)

system_prompt = """You are a geospatial analyst for Peru wildfire data.

When asked to analyze fires, load and follow the peru-fire-analysis skill.
Report statistics after aggregation.
When generating maps, the map will be automatically displayed in the chat - no file downloads needed."""

# Get the directory where this script lives (for skills path)
SCRIPT_DIR = Path(__file__).parent.resolve()

# Definir un agente con un modelo local
agent = create_deep_agent(
    model=local_llm,
    tools=[download_viirs_snpp_peru, fires_clean, download_ctry_shp,
           intersect_and_collapse_fires_peru, folium_choropleth_peru],
    system_prompt=system_prompt,
    skills=[str(SCRIPT_DIR)],  # Points to folder with SKILL.md
    checkpointer=InMemorySaver()  # Persists conversation state across turns, keyed by thread_id
)
