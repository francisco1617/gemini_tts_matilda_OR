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

    # Voces nativas de Gemini 3.1 Flash TTS (verificado via OpenRouter API)
    _supported_voices = [
        Voice("Zephyr", "Zephyr (Bright)"),
        Voice("Puck", "Puck (Upbeat)"),
        Voice("Charon", "Charon (Informative)"),
        Voice("Kore", "Kore (Firm)"),
        Voice("Fenrir", "Fenrir (Firm)"),
        Voice("Leda", "Leda (Youthful)"),
        Voice("Orus", "Orus (Firm)"),
        Voice("Aoede", "Aoede (Breezy)"),
        Voice("Callirrhoe", "Callirrhoe (Easy-going)"),
        Voice("Autonoe", "Autonoe (Bright)"),
        Voice("Enceladus", "Enceladus (Breathy)"),
        Voice("Iapetus", "Iapetus (Clear)"),
        Voice("Umbriel", "Umbriel (Easy-going)"),
        Voice("Algieba", "Algieba (Efficient)"),
        Voice("Despina", "Despina (Casual)"),
        Voice("Erinome", "Erinome (Casual)"),
        Voice("Algenib", "Algenib (Dry)"),
        Voice("Rasalgethi", "Rasalgethi (Informative)"),
        Voice("Laomedeia", "Laomedeia (Upbeat)"),
        Voice("Achernar", "Achernar (Soft)"),
        Voice("Alnilam", "Alnilam (Airy)"),
        Voice("Schedar", "Schedar (Even)"),
        Voice("Gacrux", "Gacrux (Calm)"),
        Voice("Pulcherrima", "Pulcherrima (Fast)"),
        Voice("Achird", "Achird (Friendly)"),
        Voice("Zubenelgenubi", "Zubenelgenubi (Casual)"),
        Voice("Vindemiatrix", "Vindemiatrix (Gentle)"),
        Voice("Sadachbia", "Sadachbia (Fun)"),
        Voice("Sadaltager", "Sadaltager (Knowledgeable)"),
        Voice("Sulafat", "Sulafat (Warm)"),
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
        Returns WAV (PCM with header) so HA's ffmpeg pipeline can decode it.
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
        voice = options.get(ATTR_VOICE, self._supported_voices[0].voice_id)

        # OpenRouter exige response_format=pcm para Gemini TTS
        # Gemini 3.1 Flash TTS produce: PCM 24kHz / 16-bit / mono
        payload = {
            "model": model,
            "input": full_message,
            "voice": voice,
            "response_format": "pcm",
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
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                content_type = resp.headers.get("Content-Type", "")
                LOGGER.info(
                    "OpenRouter TTS response: status=%s content_type=%s size=%s",
                    resp.status, content_type, resp.headers.get("Content-Length", "?"),
                )

                if resp.status != 200:
                    body = await resp.text()
                    LOGGER.error(
                        "OpenRouter TTS error %s: %s", resp.status, body[:500]
                    )
                    raise HomeAssistantError(
                        f"OpenRouter TTS failed (HTTP {resp.status}): {body[:200]}"
                    )

                # Verificar que realmente recibimos audio, no un JSON de error
                if "audio" not in content_type:
                    body = await resp.text()
                    LOGGER.error(
                        "OpenRouter TTS no-audio response: content_type=%s body=%s",
                        content_type, body[:500],
                    )
                    raise HomeAssistantError(
                        f"OpenRouter returned non-audio: {content_type}"
                    )

                pcm_bytes = await resp.read()
                if not pcm_bytes:
                    raise HomeAssistantError("Empty audio response from OpenRouter")

                # Envolver PCM crudo en header WAV para que ffmpeg pueda decodificar
                wav_bytes = self._pcm_to_wav(pcm_bytes)
                LOGGER.info(
                    "OpenRouter TTS OK: pcm=%s bytes -> wav=%s bytes",
                    len(pcm_bytes), len(wav_bytes),
                )
                return "wav", wav_bytes

        except aiohttp.ClientError as exc:
            LOGGER.error("OpenRouter connection error: %s", exc)
            raise HomeAssistantError(f"OpenRouter connection failed: {exc}") from exc
        except TimeoutError as exc:
            LOGGER.error("OpenRouter TTS timeout (120s) for text: %s", message[:50])
            raise HomeAssistantError(
                "OpenRouter TTS timeout — el modelo tardó más de 120s"
            ) from exc

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes) -> bytes:
        """Wrap raw PCM bytes in a WAV header.

        Gemini 3.1 Flash TTS outputs PCM 24kHz / 16-bit / mono.
        Without a WAV header, HA's ffmpeg cannot decode the raw PCM.
        """
        import struct

        sample_rate = 24000
        bits_per_sample = 16
        channels = 1
        num_samples = len(pcm_data) // (bits_per_sample // 8 * channels)
        data_size = len(pcm_data)

        # WAV header = 44 bytes
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",                    # ChunkID
            36 + data_size,             # ChunkSize
            b"WAVE",                    # Format
            b"fmt ",                    # Subchunk1ID
            16,                         # Subchunk1Size (PCM)
            1,                          # AudioFormat (1 = PCM)
            channels,                   # NumChannels
            sample_rate,                # SampleRate
            sample_rate * channels * (bits_per_sample // 8),  # ByteRate
            channels * (bits_per_sample // 8),                 # BlockAlign
            bits_per_sample,            # BitsPerSample
            b"data",                    # Subchunk2ID
            data_size,                  # Subchunk2Size
        )

        return header + pcm_data
