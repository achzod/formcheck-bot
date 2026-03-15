from __future__ import annotations

import unittest

from app.config import (
    minimax_internal_worker_token,
    minimax_remote_worker_effective_enabled,
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
            "render_api_key": settings.render_api_key,
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


if __name__ == "__main__":
    unittest.main()
