from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from app import media_handler


class MediaHandlerStorageTests(unittest.TestCase):
    def test_media_root_dir_prefers_explicit_env(self) -> None:
        with mock.patch.object(media_handler.os, "getenv", return_value="/tmp/formcheck-media"):
            self.assertEqual(media_handler._media_root_dir(), Path("/tmp/formcheck-media"))

    def test_media_root_dir_uses_persistent_state_when_available(self) -> None:
        original_exists = Path.exists

        def fake_exists(path_obj: Path) -> bool:
            if str(path_obj) == "/app/state":
                return True
            return original_exists(path_obj)

        with mock.patch.object(media_handler.os, "getenv", return_value=""):
            with mock.patch.object(Path, "exists", autospec=True, side_effect=fake_exists):
                self.assertEqual(media_handler._media_root_dir(), Path("/app/state/media"))

    def test_media_root_dir_falls_back_to_local_media(self) -> None:
        original_exists = Path.exists

        def fake_exists(path_obj: Path) -> bool:
            if str(path_obj) == "/app/state":
                return False
            return original_exists(path_obj)

        with mock.patch.object(media_handler.os, "getenv", return_value=""):
            with mock.patch.object(Path, "exists", autospec=True, side_effect=fake_exists):
                self.assertEqual(media_handler._media_root_dir(), Path("media"))


if __name__ == "__main__":
    unittest.main()
