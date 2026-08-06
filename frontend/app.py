import streamlit as st

from src.api_client import backend_health

st.set_page_config(
    page_title="AI LinkedIn Content Agent",
    page_icon=":material/edit_square:",
    layout="wide",
)

st.sidebar.title("Content Agent")
st.sidebar.caption("Phase 1 foundation")

st.title("AI LinkedIn Content Agent")
st.write("The local application foundation is running.")

health = backend_health()
if health.get("status") == "ok":
    st.success("Backend connected")
else:
    st.error("Backend unavailable")
    st.code(health.get("detail", "Unknown connection error"))

st.info(
    "Feature workflows, database models, integrations, and application pages will be "
    "implemented in their requested phases."
)
