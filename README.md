# Gemini TTS Matilda (OpenRouter)

Custom Home Assistant integration for Google Gemini TTS via **OpenRouter** with Director's Prompt injection.

Same as `gemini_tts_matilda` but uses OpenRouter's OpenAI-compatible TTS endpoint instead of the Google SDK. No `google-genai` dependency — just `aiohttp`.

## What it does

Injects a **Director's Prompt** (voice character profile) before every text-to-speech request sent to OpenRouter's Gemini TTS endpoint. The prompt controls tone, timbre, cadence, and attitude so your assistant sounds like the same character every time.

## Installation

### HACS (recommended)
1. HACS → Integrations → ⋮ (3 dots) → Custom repositories
2. Add `https://github.com/francisco1617/gemini_tts_matilda_OR` as Integration
3. Search "Gemini TTS Matilda (OpenRouter)" and download
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → Gemini TTS Matilda (OpenRouter)

### Manual
1. Copy `custom_components/gemini_tts_matilda_OR/` to your HA `config/custom_components/`
2. Restart Home Assistant
3. Add the integration via Settings → Devices & Services

## Configuration

| Field | Description | Default |
|---|---|---|
| API Key | Your OpenRouter API key | Required |
| TTS Model | Gemini TTS model on OpenRouter | `google/gemini-3.1-flash-tts-preview` |
| Temperature | Creativity for voice (0.0-2.0) | 1.0 |
| Director's Prompt | Voice character profile injected before every TTS | Matilda's voice profile |

## Director's Prompt

The default prompt is Matilda's voice profile:

```
# AUDIO PROFILE: Matilda — pequeña hada de batalla mexicana

Tono: soprano agudo, dulce, suave, con aire aspirado.
Cadencia: fluctuante, melódica, vocales alargadas, siempre emocionada.
Actitud: inocente, asombrada, juguetona, siempre lista para pelear.

#### TRANSCRIPT
```

## Pricing

OpenRouter pricing for `google/gemini-3.1-flash-tts-preview`:
- $1.00 per 1M input tokens
- $20.00 per 1M output tokens

## License

MIT
