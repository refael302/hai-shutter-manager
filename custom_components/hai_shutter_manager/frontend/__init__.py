"""Serve the Lovelace card from the integration and keep the resource current."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..const import (
    FRONTEND_CARD_FILENAME,
    FRONTEND_URL_BASE,
    INTEGRATION_VERSION,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def card_url() -> str:
    return f"{FRONTEND_URL_BASE}/{FRONTEND_CARD_FILENAME}"


def versioned_url(version: str = INTEGRATION_VERSION) -> str:
    return f"{card_url()}?v={version}"


def path_only(url: str) -> str:
    return url.split("?", 1)[0]


def version_of(url: str) -> str:
    if "?v=" not in url:
        return ""
    return url.split("?v=", 1)[1]


def classify_resources(
    items: list[dict[str, Any]],
    *,
    our_url: str,
    filename: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split Lovelace resources into ours vs legacy copies of the same file."""
    ours: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    for item in items:
        path = path_only(item.get("url", ""))
        if path == our_url:
            ours.append(item)
        elif path.endswith(f"/{filename}"):
            legacy.append(item)
    return ours, legacy


def _get_resources(hass: HomeAssistant) -> Any | None:
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return None
    resources = getattr(lovelace, "resources", None)
    if resources is not None:
        return resources
    try:
        return lovelace["resources"]
    except (KeyError, TypeError):
        return None


class JSModuleRegistration:
    """Register the dashboard card over HTTP and as a Lovelace resource."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_register(self) -> None:
        """Serve the JS file, then register or repair the Lovelace resource."""
        path_ok = await self._async_register_path()
        if not path_ok:
            _LOGGER.error(
                "Could not serve the dashboard card from %s; "
                "leaving existing Lovelace resources in place",
                card_url(),
            )
            return

        resources = _get_resources(self.hass)
        if resources is None:
            self._add_extra_js()
            return

        if hasattr(resources, "async_create_item"):
            try:
                if hasattr(resources, "async_get_info"):
                    await resources.async_get_info()
                await self._async_register_module(resources)
                return
            except Exception:
                _LOGGER.exception("Failed to register Lovelace card resource")

        self._add_extra_js()

    async def _async_register_path(self) -> bool:
        frontend_dir = Path(__file__).parent
        try:
            from homeassistant.components.http import StaticPathConfig

            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_BASE, str(frontend_dir), False)]
            )
            return True
        except RuntimeError as err:
            # Reload is fine. "HTTP server has already started" is not.
            if "already registered" in str(err).lower():
                return True
            _LOGGER.warning("Could not register card static path: %s", err)
            return False
        except AttributeError:
            try:
                self.hass.http.register_static_path(
                    FRONTEND_URL_BASE, str(frontend_dir), False
                )
                return True
            except Exception as err:
                _LOGGER.warning("Could not register card static path: %s", err)
                return False
        except Exception:
            _LOGGER.exception("Could not register card static path")
            return False

    def _add_extra_js(self) -> None:
        """YAML / fallback: inject the card into the frontend extra JS list."""
        try:
            from homeassistant.components.frontend import add_extra_js_url

            add_extra_js_url(self.hass, versioned_url())
            _LOGGER.info("Registered dashboard card via extra JS %s", versioned_url())
        except Exception:
            _LOGGER.exception("Failed to add extra JS URL for dashboard card")

    async def _async_register_module(self, resources: Any) -> None:
        url = card_url()
        versioned = versioned_url()
        ours, legacy = classify_resources(
            list(resources.async_items()),
            our_url=url,
            filename=FRONTEND_CARD_FILENAME,
        )

        # Publish the new URL first. Only then drop /local and /hacsfiles copies.
        if not ours:
            _LOGGER.info("Registering Lovelace card %s", versioned)
            await resources.async_create_item(
                {"res_type": "module", "url": versioned}
            )
        else:
            for item in ours:
                if version_of(item.get("url", "")) == INTEGRATION_VERSION:
                    continue
                _LOGGER.info("Updating Lovelace card resource to %s", versioned)
                await resources.async_update_item(
                    item["id"],
                    {"res_type": "module", "url": versioned},
                )

        for item in legacy:
            _LOGGER.info("Replacing legacy Lovelace card resource %s", item.get("url"))
            await resources.async_delete_item(item["id"])
