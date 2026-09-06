"""Tests for Lovelace card URL helpers and resource registration order."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "hai_shutter_manager"


def _load_frontend():
    """Import frontend without executing the Home Assistant integration package."""
    if "hai_shutter_manager" not in sys.modules:
        pkg = types.ModuleType("hai_shutter_manager")
        pkg.__path__ = [str(COMPONENT)]
        sys.modules["hai_shutter_manager"] = pkg

    if "hai_shutter_manager.const" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "hai_shutter_manager.const", COMPONENT / "const.py"
        )
        const = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(const)
        sys.modules["hai_shutter_manager.const"] = const

    if "hai_shutter_manager.frontend" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "hai_shutter_manager.frontend",
            COMPONENT / "frontend" / "__init__.py",
            submodule_search_locations=[str(COMPONENT / "frontend")],
        )
        frontend = importlib.util.module_from_spec(spec)
        sys.modules["hai_shutter_manager.frontend"] = frontend
        assert spec.loader is not None
        spec.loader.exec_module(frontend)
    return sys.modules["hai_shutter_manager.frontend"]


frontend = _load_frontend()


class ClassifyResourcesTests(unittest.TestCase):
    def test_versioned_url_uses_manifest_version(self) -> None:
        self.assertEqual(
            frontend.card_url(),
            "/hai-shutter-manager/hai-shutter-table-card.js",
        )
        self.assertTrue(frontend.versioned_url().endswith("?v=0.6.5"))

    def test_splits_ours_and_legacy_copies(self) -> None:
        ours, legacy = frontend.classify_resources(
            [
                {"id": "1", "url": "/hai-shutter-manager/hai-shutter-table-card.js?v=0.6.3"},
                {"id": "2", "url": "/hacsfiles/hai_shutter_manager/hai-shutter-table-card.js"},
                {"id": "3", "url": "/local/hai-shutter-table-card.js?v=1"},
                {"id": "4", "url": "/local/other-card.js"},
            ],
            our_url="/hai-shutter-manager/hai-shutter-table-card.js",
            filename="hai-shutter-table-card.js",
        )
        self.assertEqual([item["id"] for item in ours], ["1"])
        self.assertEqual([item["id"] for item in legacy], ["2", "3"])

    def test_path_and_version_helpers(self) -> None:
        self.assertEqual(
            frontend.path_only("/hai-shutter-manager/hai-shutter-table-card.js?v=0.6.4"),
            "/hai-shutter-manager/hai-shutter-table-card.js",
        )
        self.assertEqual(
            frontend.version_of("/hai-shutter-manager/hai-shutter-table-card.js?v=0.6.4"),
            "0.6.4",
        )
        self.assertEqual(frontend.version_of("/local/hai-shutter-table-card.js"), "")


class FakeResources:
    def __init__(self, items: list[dict]) -> None:
        self.items = list(items)
        self.loaded = False
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []
        self.deleted: list[str] = []
        self.order: list[str] = []

    def async_items(self) -> list[dict]:
        return list(self.items)

    async def async_get_info(self) -> dict:
        self.loaded = True
        self.order.append("load")
        return {"resources": len(self.items)}

    async def async_create_item(self, data: dict) -> dict:
        self.order.append("create")
        self.created.append(data)
        item = {"id": "new", **data}
        self.items.append(item)
        return item

    async def async_update_item(self, item_id: str, updates: dict) -> dict:
        self.order.append("update")
        self.updated.append((item_id, updates))
        return updates

    async def async_delete_item(self, item_id: str) -> None:
        self.order.append("delete")
        self.deleted.append(item_id)
        self.items = [item for item in self.items if item["id"] != item_id]


class RegistrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.hass = MagicMock()
        self.hass.data = {}
        self.hass.http.async_register_static_paths = AsyncMock()

        http_mod = types.ModuleType("homeassistant.components.http")

        class StaticPathConfig:
            def __init__(self, url_path, path, cache_headers=True):
                self.url_path = url_path
                self.path = path
                self.cache_headers = cache_headers

        http_mod.StaticPathConfig = StaticPathConfig
        sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
        sys.modules.setdefault(
            "homeassistant.components", types.ModuleType("homeassistant.components")
        )
        sys.modules["homeassistant.components.http"] = http_mod

    async def test_creates_new_resource_before_deleting_legacy(self) -> None:
        resources = FakeResources(
            [
                {
                    "id": "old",
                    "url": "/hacsfiles/hai_shutter_manager/hai-shutter-table-card.js",
                }
            ]
        )
        self.hass.data["lovelace"] = types.SimpleNamespace(resources=resources)

        await frontend.JSModuleRegistration(self.hass).async_register()

        self.assertTrue(resources.loaded)
        self.assertEqual(len(resources.created), 1)
        self.assertTrue(
            resources.created[0]["url"].startswith(
                "/hai-shutter-manager/hai-shutter-table-card.js?v="
            )
        )
        self.assertEqual(resources.deleted, ["old"])
        self.assertLess(resources.order.index("create"), resources.order.index("delete"))

    async def test_does_not_delete_legacy_when_static_path_fails(self) -> None:
        resources = FakeResources(
            [
                {
                    "id": "old",
                    "url": "/local/hai-shutter-table-card.js",
                }
            ]
        )
        self.hass.data["lovelace"] = types.SimpleNamespace(resources=resources)
        self.hass.http.async_register_static_paths = AsyncMock(
            side_effect=RuntimeError("HTTP server has already started")
        )

        await frontend.JSModuleRegistration(self.hass).async_register()

        self.assertEqual(resources.created, [])
        self.assertEqual(resources.deleted, [])

    async def test_already_registered_path_is_ok(self) -> None:
        resources = FakeResources([])
        self.hass.data["lovelace"] = types.SimpleNamespace(resources=resources)
        self.hass.http.async_register_static_paths = AsyncMock(
            side_effect=RuntimeError("Path already registered")
        )

        await frontend.JSModuleRegistration(self.hass).async_register()

        self.assertEqual(len(resources.created), 1)

    async def test_yaml_resources_fall_back_to_extra_js(self) -> None:
        yaml_resources = types.SimpleNamespace(
            loaded=True,
            async_items=lambda: [],
        )
        self.hass.data["lovelace"] = types.SimpleNamespace(resources=yaml_resources)

        extra = types.ModuleType("homeassistant.components.frontend")
        extra.add_extra_js_url = MagicMock()
        sys.modules["homeassistant.components.frontend"] = extra

        await frontend.JSModuleRegistration(self.hass).async_register()

        extra.add_extra_js_url.assert_called_once()
        self.assertIn(
            "/hai-shutter-manager/hai-shutter-table-card.js?v=",
            extra.add_extra_js_url.call_args[0][1],
        )

    async def test_forces_storage_load_instead_of_waiting_for_loaded_flag(self) -> None:
        resources = FakeResources([])
        self.assertFalse(resources.loaded)
        self.hass.data["lovelace"] = types.SimpleNamespace(resources=resources)

        await frontend.JSModuleRegistration(self.hass).async_register()

        self.assertTrue(resources.loaded)
        self.assertEqual(resources.order[0], "load")


class CardFileTests(unittest.TestCase):
    def test_card_js_defines_custom_element(self) -> None:
        source = (COMPONENT / "frontend" / "hai-shutter-table-card.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('customElements.define("hai-shutter-table-card"', source)
        self.assertIn("setConfig(config)", source)
        self.assertIn("_syncUnsafe()", source)
        self.assertIn("@container hai-shutter (min-width: 840px)", source)
        self.assertIn("table-wrap", source)
        self.assertIn("_tableTemplate", source)
        self.assertIn("_cardTemplate", source)


if __name__ == "__main__":
    unittest.main()
