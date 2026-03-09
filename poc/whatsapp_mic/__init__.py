import os
import streamlit.components.v1 as components

# Create a wrapper function for the component
_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "whatsapp_mic",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    _component_func = components.declare_component("whatsapp_mic", path=parent_dir)

def whatsapp_mic(key=None):
    component_value = _component_func(key=key, default=None)
    return component_value
