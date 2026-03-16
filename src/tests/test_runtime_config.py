from __future__ import annotations

import unittest

from app.config import (
    minimax_internal_worker_token,
    minimax_internal_worker_tokens,
    minimax_remote_worker_effective_enabled,
    minimax_remote_worker_id_allowed,
    settings,
)


class MiniMaxRuntimeConfigTests(unittest.TestCase):
    def _snapshot(self) -> dict[str, object]:
        return {
            "minimax_enabled": settings.minimax_enabled,
            "minimax_browser_only": settings.minimax_browser_only,
            "minimax_strict_source": settings.minimax_strict_source,
            "minimax_fallback_to_local": settings.minimax_fallback_to_local,
            "minimax_remote_worker_enabled": settings.minimax_remote_worker_enabled,
            "minimax_remote_worker_token": settings.minimax_remote_worker_token,
            "minimax_remote_worker_allowed_ids": settings.minimax_remote_worker_allowed_ids,
            "minimax_remote_worker_allowed_prefixes": settings.minimax_remote_worker_allowed_prefixes,
            "render_api_key": settings.render_api_key,
            "base_url": settings.base_url,
            "test_mode": settings.test_mode,
        }

    def _restore(self, snapshot: dict[str, object]) -> None:
        for key, value in snapshot.items():
            setattr(settings, key, value)

    def test_internal_worker_token_prefers_explicit_remote_worker_token(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.minimax_remote_worker_token = "worker-token"
            settings.render_api_key = "render-token"
            self.assertEqual(minimax_internal_worker_token(settings), "worker-token")
        finally:
            self._restore(snapshot)

    def test_internal_worker_tokens_include_render_api_key_without_duplicates(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.minimax_remote_worker_token = "worker-token"
            settings.render_api_key = "render-token"
            self.assertEqual(
                minimax_internal_worker_tokens(settings),
                ("worker-token", "render-token"),
            )
            settings.render_api_key = "worker-token"
            self.assertEqual(
                minimax_internal_worker_tokens(settings),
                ("worker-token",),
            )
        finally:
            self._restore(snapshot)

    def test_remote_worker_effective_enabled_honors_explicit_flag(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.minimax_remote_worker_enabled = True
            settings.minimax_enabled = True
            settings.minimax_browser_only = False
            settings.minimax_strict_source = False
            settings.minimax_fallback_to_local = True
            settings.minimax_remote_worker_token = ""
            settings.render_api_key = ""
            self.assertTrue(minimax_remote_worker_effective_enabled(settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_effective_enabled_recovers_from_boolean_env_drift(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.minimax_enabled = True
            settings.minimax_browser_only = True
            settings.minimax_strict_source = True
            settings.minimax_fallback_to_local = False
            settings.minimax_remote_worker_enabled = False
            settings.minimax_remote_worker_token = "worker-token"
            settings.render_api_key = ""
            self.assertTrue(minimax_remote_worker_effective_enabled(settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_effective_enabled_rejects_fallback_local_mode(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.minimax_enabled = True
            settings.minimax_browser_only = True
            settings.minimax_strict_source = True
            settings.minimax_fallback_to_local = True
            settings.minimax_remote_worker_enabled = False
            settings.minimax_remote_worker_token = "worker-token"
            settings.render_api_key = ""
            self.assertFalse(minimax_remote_worker_effective_enabled(settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_effective_enabled_rejects_missing_internal_token(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.minimax_enabled = True
            settings.minimax_browser_only = True
            settings.minimax_strict_source = True
            settings.minimax_fallback_to_local = False
            settings.minimax_remote_worker_enabled = False
            settings.minimax_remote_worker_token = ""
            settings.render_api_key = ""
            self.assertFalse(minimax_remote_worker_effective_enabled(settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_id_allowed_accepts_render_worker_by_default(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.base_url = "https://formcheck-bot.onrender.com"
            settings.test_mode = False
            settings.minimax_remote_worker_allowed_ids = ""
            settings.minimax_remote_worker_allowed_prefixes = ""
            self.assertTrue(minimax_remote_worker_id_allowed("srv-d6o382rh46gs73a59h8g-x5jh7-1", settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_id_allowed_rejects_local_hostname_in_prod(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.base_url = "https://formcheck-bot.onrender.com"
            settings.test_mode = False
            settings.minimax_remote_worker_allowed_ids = ""
            settings.minimax_remote_worker_allowed_prefixes = ""
            self.assertFalse(minimax_remote_worker_id_allowed("MacBook-Pro-de-achkan.local-60518", settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_id_allowed_honors_explicit_ids(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.base_url = "https://formcheck-bot.onrender.com"
            settings.test_mode = False
            settings.minimax_remote_worker_allowed_ids = "worker-a,worker-b"
            settings.minimax_remote_worker_allowed_prefixes = ""
            self.assertTrue(minimax_remote_worker_id_allowed("worker-b", settings))
            self.assertFalse(minimax_remote_worker_id_allowed("srv-d6o382rh46gs73a59h8g-x5jh7-1", settings))
        finally:
            self._restore(snapshot)

    def test_remote_worker_id_allowed_allows_local_dev_base_url(self) -> None:
        snapshot = self._snapshot()
        try:
            settings.base_url = "http://127.0.0.1:8000"
            settings.test_mode = False
            settings.minimax_remote_worker_allowed_ids = ""
            settings.minimax_remote_worker_allowed_prefixes = ""
            self.assertTrue(minimax_remote_worker_id_allowed("MacBook-Pro-de-achkan.local-60518", settings))
        finally:
            self._restore(snapshot)


if __name__ == "__main__":
    unittest.main()
