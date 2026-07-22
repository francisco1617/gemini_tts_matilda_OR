"""Constants for the Gemini TTS Matilda (OpenRouter) integration."""

import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "gemini_tts_matilda_OR"
DEFAULT_TITLE = "Gemini TTS Matilda (OpenRouter)"

CONF_CHAT_MODEL = "chat_model"
RECOMMENDED_TTS_MODEL = "google/gemini-3.1-flash-tts-preview"
CONF_TEMPERATURE = "temperature"
RECOMMENDED_TEMPERATURE = 1.0

# OpenRouter endpoint
OPENROUTER_TTS_URL = "https://openrouter.ai/api/v1/audio/speech"

# The Director's Prompt — voice profile for Matilda
# Injected before every TTS call to give Gemini consistent character
CONF_TTS_PROMPT = "tts_prompt"
RECOMMENDED_TTS_PROMPT = """# AUDIO PROFILE: Matilda — pequeña hada de batalla mexicana

Tono: soprano agudo, dulce, suave, con aire aspirado.
Cadencia: fluctuante, melódica, vocales alargadas, siempre emocionada.
Actitud: inocente, asombrada, juguetona, siempre lista para pelear.

#### TRANSCRIPT
"""

RECOMMENDED_TTS_OPTIONS = {}
