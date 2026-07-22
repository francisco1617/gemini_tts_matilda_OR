"""Text to speech support for Gemini TTS Matilda (OpenRouter).

Uses OpenRouter's OpenAI-compatible TTS endpoint instead of the Google SDK.
Injects the Director's Prompt (CONF_TTS_PROMPT) before every TTS call.
"""

from collections.abc import Mapping
from typing import Any, override

import aiohttp

from homeassistant.components.tts import (
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_CHAT_MODEL,
    CONF_TTS_PROMPT,
    DOMAIN,
    LOGGER,
    OPENROUTER_TTS_URL,
    RECOMMENDED_TTS_MODEL,
    RECOMMENDED_TTS_PROMPT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up TTS entities."""
    async_add_entities(
        [MatildaOREntity(hass, config_entry)],
    )


class MatildaOREntity(TextToSpeechEntity, Entity):
    """Gemini TTS entity via OpenRouter with Director's Prompt injection."""

    _attr_supported_options = [ATTR_VOICE, CONF_TTS_PROMPT]
    _attr_supported_languages = [
        "af-ZA", "am-ET", "ar-EG", "az-AZ", "be-BY", "bg-BG", "bn-BD",
        "ca-ES", "ceb-PH", "cmn-CN", "cs-CZ", "da-DK", "de-DE", "el-GR",
        "en-IN", "en-US", "es-ES", "es-US", "et-EE", "eu-ES", "fa-IR",
        "fi-FI", "fil-PH", "fr-FR", "gl-ES", "gu-IN", "he-IL", "hi-IN",
        "hr-HR", "ht-HT", "hu-HU", "hy-AM", "id-ID", "is-IS", "it-IT",
        "ja-JP", "jv-ID", "ka-GE", "kn-IN", "ko-KR", "kok-IN", "la-VA",
        "lb-LU", "lo-LA", "lt-LT", "lv-LV", "mai-IN", "mg-MG", "mk-MK",
        "ml-IN", "mn-MN", "mr-IN", "ms-MY", "my-MM", "nb-NO", "ne-NP",
        "nl-NL", "nn-NO", "or-IN", "pa-IN", "pl-PL", "ps-AF", "pt-BR",
        "pt-PT", "ro-RO", "ru-RU", "sd-PK", "si-LK", "sk-SK", "sl-SI",
        "sq-AL", "sr-RS", "sv-SE", "sw-KE", "ta-IN", "te-IN", "th-TH",
        "tr-TR", "uk-UA", "ur-PK", "vi-VN",
    ]
    _attr_default_language = "en-US"

    _supported_voices = [
        Voice(voice.split(" ", 1)[0].lower(), voice)
        for voice in (
            "Zephyr (Bright)", "Puck (Upbeat)", "Charon (Informative)",
            "Kore (Firm)", "Fenrir (Excitable)", "Leda (Youthful)",
            "Orus (Firm)", "Aoede (Breezy)", "Callirrhoe (Easy-going)",
            "Autonoe (Bright)", "Enceladus (Breathy)", "Iapetus (Clear)",
            "Umbriel (Easy-going)", "Algieba (Smooth)", "Despina (Smooth)",
            "Erinome (Clear)", "Algenib (Gravelly)", "Rasalgethi (Informative)",
            "Laomedeia (Upbeat)", "Achernar (Soft)", "Alnilam (Firm)",
            "Schedar (Even)", "Gacrux (Mature)", "Pulcherrima (Forward)",
            "Achird (Friendly)", "Zubenelgenubi (Casual)",
            "Vindemiatrix (Gentle)", "Sadachbia (Lively)",
            "Sadaltager (Knowledgeable)", "Sulafat (Warm)",
        )
    ]

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the TTS entity."""
        self.hass = hass
        self.config_entry = config_entry
        self._api_key = config_entry.runtime_data
        self._attr_name = config_entry.title
        self._attr_unique_id = config_entry.entry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Google (via OpenRouter)",
            model=RECOMMENDED_TTS_MODEL.split("/")[-1],
            entry_type=dr.DeviceEntryType.SERVICE,
        )
        self._last_prompt_preview = ""

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return additional state attributes for diagnostics."""
        return {
            "prompt_active": bool(self._last_prompt_preview),
            "prompt_preview": self._last_prompt_preview,
        }

    @callback
    @override
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        """Return a list of supported voices for a language."""
        return self._supported_voices

    @property
    @override
    def default_options(self) -> Mapping[str, Any]:
        """Return a mapping with the default options."""
        return {
            ATTR_VOICE: self._supported_voices[0].voice_id,
            CONF_TTS_PROMPT: RECOMMENDED_TTS_PROMPT,
        }

    @override
    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Load tts audio from OpenRouter.

        Injects the Director's Prompt before the message and sends
        to OpenRouter's OpenAI-compatible TTS endpoint.
        """
        # === KEY MODIFICATION: inject Director's Prompt before message ===
        prompt = options.get(CONF_TTS_PROMPT) or self.config_entry.options.get(
            CONF_TTS_PROMPT, RECOMMENDED_TTS_PROMPT
        )
        full_message = prompt + "\n" + message if prompt else message

        # Log para verificar que el prompt se inyectó
        if prompt:
            preview = prompt.strip().split("\n")[0][:60]
            self._last_prompt_preview = preview
            LOGGER.info(
                "TTS con Director's Prompt: %s | texto: %s",
                preview, message[:50],
            )
        else:
            self._last_prompt_preview = ""
            LOGGER.warning(
                "TTS sin Director's Prompt — solo texto crudo: %s", message[:50]
            )

        model = self.config_entry.options.get(
            CONF_CHAT_MODEL, RECOMMENDED_TTS_MODEL
        )
        voice = options.get(ATTR_VOICE, "Kore")

        payload = {
            "model": model,
            "input": full_message,
            "voice": voice,
            "response_format": "wav",
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                OPENROUTER_TTS_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    LOGGER.error(
                        "OpenRouter TTS error %s: %s", resp.status, body[:200]
                    )
                    raise HomeAssistantError(
                        f"OpenRouter TTS failed (HTTP {resp.status})"
                    )

                audio_bytes = await resp.read()
                if not audio_bytes:
                    raise HomeAssistantError("Empty audio response from OpenRouter")

                return "wav", audio_bytes

        except aiohttp.ClientError as exc:
            LOGGER.error("OpenRouter connection error: %s", exc)
            raise HomeAssistantError(f"OpenRouter connection failed: {exc}") from exc
