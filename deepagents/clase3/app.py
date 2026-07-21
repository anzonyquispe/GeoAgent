import streamlit as st
from streamlit_folium import st_folium
from agent import agent
from tools import get_session_data, clear_session_data
from extraction import extract_query
import uuid

def generate_response(input_text, thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    prior_state = agent.get_state(config)
    prior_count = len(prior_state.values.get("messages", [])) if prior_state.values else 0

    response = agent.invoke(
        {"messages": [{"role": "user",
                       "content": input_text}]},
        config=config
    )

    new_messages = response["messages"][prior_count:]
    tool_calls = _pair_tool_calls(new_messages)
    return response, tool_calls


def _pair_tool_calls(messages):
    """Match each AIMessage tool call with its ToolMessage result, for the monitor panel."""
    calls = []
    pending = {}
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            pending[tc["id"]] = {"tool": tc["name"], "args": tc["args"]}
        if type(m).__name__ == "ToolMessage":
            call = pending.get(m.tool_call_id, {"tool": getattr(m, "name", "?"), "args": {}})
            calls.append({**call, "result": m.content})
    return calls


def render_monitor(extracted, tool_calls):
    with st.expander("🔍 Monitor del agente"):
        st.markdown("**Extracción estructurada del input (Pydantic):**")
        st.json(extracted)
        st.markdown("**Tool calls ejecutadas este turno:**")
        if tool_calls:
            st.table(tool_calls)
        else:
            st.caption("No se ejecutaron tools en este turno.")


st.set_page_config(page_title="Chatbot especializado en incendios forestales en Perú 🔥🌲", layout="wide")
st.title("Chatbot especializado en incendios forestales en Perú 🔥🌲")

with st.sidebar:
    st.header("Opciones")
    show_monitor = st.checkbox("🔍 Monitor de llamadas del agente", value=True)
    st.caption(
        "Muestra qué se extrajo del texto libre del usuario (structured output) "
        "y qué tools ejecutó el agente para responder."
    )

# Initialize chat history and thread_id
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If this message has an associated map, display it
        if "map" in message:
            st_folium(message["map"], width=700, height=500, returned_objects=[])
        if show_monitor and "extracted" in message:
            render_monitor(message["extracted"], message.get("tool_calls", []))

# Accept user input
if prompt := st.chat_input("Ask about Peru wildfires..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        extracted = extract_query(prompt)
        response, tool_calls = generate_response(prompt, st.session_state.thread_id)
        content = response["messages"][-1].content

        # Handle both string and content blocks format
        if isinstance(content, str):
            response_text = content
        else:
            response_text = content[0]['text']

        st.markdown(response_text)

        if show_monitor:
            render_monitor(extracted.model_dump(), tool_calls)

        # Check if there's a pending map to display
        session_data = get_session_data()
        pending_map = session_data.pop("pending_map", None)
        map_title = session_data.pop("map_title", None)

        assistant_message = {
            "role": "assistant",
            "content": response_text,
            "extracted": extracted.model_dump(),
            "tool_calls": tool_calls,
        }

        if pending_map is not None:
            if map_title:
                st.subheader(map_title)
            st_folium(pending_map, width=700, height=500, returned_objects=[])
            assistant_message["map"] = pending_map

        st.session_state.messages.append(assistant_message)
