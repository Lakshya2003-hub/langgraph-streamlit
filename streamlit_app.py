import streamlit as st
import requests
import json
from typing import List, Dict
from datetime import datetime

# Configuration
API_BASE_URL = st.sidebar.text_input(
    "API Base URL",
    value="http://localhost:3000",
    help="Base URL of the LangGraph API server"
)

# Session state initialization
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'thread_id' not in st.session_state:
    st.session_state.thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

if 'api_available' not in st.session_state:
    st.session_state.api_available = False

# Page configuration
st.set_page_config(
    page_title="LangGraph Chat",
    page_icon="🤖",
    layout="wide"
)

# Sidebar
st.sidebar.title("🤖 LangGraph Chat")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Thread ID:** `{st.session_state.thread_id}`")

# Check API health
def check_api_health():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException as e:
        return None

# Load conversation history from API
def load_history():
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/history/{st.session_state.thread_id}",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('history', [])
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error loading history: {str(e)}")
        return []

# Send message to API
def send_message(message: str) -> Dict:
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json={
                "message": message,
                "threadId": st.session_state.thread_id
            },
            timeout=60  # Increased timeout for LLM responses
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API error: {response.status_code}",
                "response": response.text
            }
    except requests.exceptions.Timeout:
        return {
            "error": "Request timeout",
            "response": "The request took too long. Please try again."
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": str(e),
            "response": f"Error connecting to API: {str(e)}"
        }

# Check API health on load
with st.sidebar:
    if st.button("🔄 Check API Status"):
        health = check_api_health()
        if health:
            st.success("✅ API is available")
            st.session_state.api_available = True
            if health.get('initialized'):
                st.success("✅ Graph service initialized")
            else:
                st.warning("⚠️ Graph service not initialized")
        else:
            st.error("❌ API is not available")
            st.session_state.api_available = False

# Load history on first load
if not st.session_state.messages:
    st.session_state.api_available = check_api_health() is not None
    if st.session_state.api_available:
        history = load_history()
        if history:
            # Convert history to messages format
            for msg in history:
                role = msg.get('role', 'assistant')
                content = msg.get('content', '')
                st.session_state.messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": msg.get('timestamp')
                })

# Main chat interface
st.title("🤖 LangGraph Chat Interface")
st.markdown("Chat with your LangGraph-powered assistant")

# Display API status
if st.session_state.api_available:
    st.success("✅ Connected to API")
else:
    st.error("❌ API not available. Please check the API server is running.")
    st.info(f"Make sure the API server is running at: {API_BASE_URL}")

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                st.markdown(content)
                if message.get("timestamp"):
                    timestamp = datetime.fromtimestamp(message["timestamp"] / 1000)
                    st.caption(f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    if not st.session_state.api_available:
        st.error("API is not available. Please check the API server is running.")
        st.stop()
    
    # Show loading indicator while processing
    with st.spinner("Thinking..."):
        # Send message to API
        result = send_message(prompt)
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
            response_text = result.get('response', 'No response received')
            # Add error message to history
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "timestamp": int(datetime.now().timestamp() * 1000)
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Error: {response_text}",
                "timestamp": int(datetime.now().timestamp() * 1000)
            })
        else:
            # Update conversation history from API response
            if 'conversationHistory' in result and result['conversationHistory']:
                # Replace entire conversation history with the one from API
                st.session_state.messages = []
                for msg in result['conversationHistory']:
                    st.session_state.messages.append({
                        "role": msg.get('role', 'assistant'),
                        "content": msg.get('content', ''),
                        "timestamp": msg.get('timestamp')
                    })
            else:
                # Fallback: add user and assistant messages manually
                response_text = result.get('response', 'No response received')
                st.session_state.messages.append({
                    "role": "user",
                    "content": prompt,
                    "timestamp": int(datetime.now().timestamp() * 1000)
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": int(datetime.now().timestamp() * 1000)
                })
    
    # Rerun to display updated messages
    st.rerun()

# Sidebar actions
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.session_state.thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.rerun()

if st.sidebar.button("📥 Load History"):
    if st.session_state.api_available:
        history = load_history()
        if history:
            st.session_state.messages = []
            for msg in history:
                st.session_state.messages.append({
                    "role": msg.get('role', 'assistant'),
                    "content": msg.get('content', ''),
                    "timestamp": msg.get('timestamp')
                })
            st.success(f"Loaded {len(history)} messages")
            st.rerun()
        else:
            st.info("No history found")
    else:
        st.error("API is not available")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
This is a Streamlit UI for the LangGraph API.
The API handles conversation history and context automatically.
""")

