import streamlit as st


################# AGENTE #################

from deepagents import create_deep_agent

# Importar api key desde las variables de entorno
from dotenv import load_dotenv
load_dotenv()


system_prompt = """
You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""

import os
from typing import Literal

from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# Definir un agente con el modelo Gemini 3.5 Flash de Google GenAI
agent = create_deep_agent(
    model="google_genai:gemini-2.5-flash",
    tools = [internet_search],
    system_prompt=system_prompt,
)

################# AGENTE #################


def generate_response(input_text):
    response = agent.invoke(
        {"messages": [{"role": "user", 
                       "content": input_text}]}
    )
    return response
    

st.title("Simple chat")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = generate_response(prompt)
        content = response["messages"][-1].content

        # Handle both string and content blocks format
        if isinstance(content, str):
            response_text = content
        else:
            response_text = content[0]['text']
            
        st.markdown(response_text)
        
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_text})