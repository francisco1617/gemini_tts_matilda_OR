"""Config flow for Gemini TTS Matilda (OpenRouter)."""

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow

from .const import (
    CONF_CHAT_MODEL,
    CONF_TEMPERATURE,
    CONF_TTS_PROMPT,
    DEFAULT_TITLE,
    DOMAIN,
    LOGGER,
    RECOMMENDED_TTS_MODEL,
    RECOMMENDED_TTS_PROMPT,
)


class GeminiTTSMatildaORConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gemini TTS Matilda (OpenRouter)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                import aiohttp

                # Quick validation: check if the API key works
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://openrouter.ai/api/v1/auth/key",
                        headers={"Authorization": f"Bearer {user_input['api_key']}"},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}")

                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={
                        "api_key": user_input["api_key"],
                    },
                    options={
                        CONF_CHAT_MODEL: user_input.get(
                            CONF_CHAT_MODEL, RECOMMENDED_TTS_MODEL
                        ),
                        CONF_TEMPERATURE: user_input.get(
                            CONF_TEMPERATURE, 1.0
                        ),
                        CONF_TTS_PROMPT: user_input.get(
                            CONF_TTS_PROMPT, RECOMMENDED_TTS_PROMPT
                        ),
                    },
                )
            except Exception as exc:
                LOGGER.error("API key validation failed: %s", exc)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key"): str,
                    vol.Optional(
                        CONF_CHAT_MODEL, default=RECOMMENDED_TTS_MODEL
                    ): str,
                    vol.Optional(CONF_TEMPERATURE, default=1.0): vol.Coerce(float),
                    vol.Optional(
                        CONF_TTS_PROMPT, default=RECOMMENDED_TTS_PROMPT
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "api_key_url": "https://openrouter.ai/keys"
            },
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthentication (API key change)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth with new API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://openrouter.ai/api/v1/auth/key",
                        headers={"Authorization": f"Bearer {user_input['api_key']}"},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status}")

                entry = self._get_reauth_entry()
                self.hass.config_entries.async_update_entry(
                    entry, data={"api_key": user_input["api_key"]}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except Exception as exc:
                LOGGER.error("API key validation failed: %s", exc)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("api_key"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "api_key_url": "https://openrouter.ai/keys"
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Return the options flow handler."""
        return GeminiTTSMatildaOROptionsFlow()


class GeminiTTSMatildaOROptionsFlow(OptionsFlow):
    """Handle options flow for Gemini TTS Matilda (OpenRouter)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            new_key = user_input.pop("api_key", "").strip()
            if new_key:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={"api_key": new_key},
                )

            return self.async_create_entry(
                title="",
                data=user_input,
            )

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "api_key",
                        default="",
                    ): str,
                    vol.Optional(
                        CONF_CHAT_MODEL,
                        default=current.get(
                            CONF_CHAT_MODEL, RECOMMENDED_TTS_MODEL
                        ),
                    ): str,
                    vol.Optional(
                        CONF_TEMPERATURE,
                        default=current.get(CONF_TEMPERATURE, 1.0),
                    ): vol.Coerce(float),
                    vol.Optional(
                        CONF_TTS_PROMPT,
                        default=current.get(
                            CONF_TTS_PROMPT, RECOMMENDED_TTS_PROMPT
                        ),
                    ): str,
                }
            ),
            description_placeholders={},
        )
