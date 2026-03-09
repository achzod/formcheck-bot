from __future__ import annotations

import unittest

from app import messages as msg


class SupportMessagesTests(unittest.TestCase):
    def test_menu_exposes_support_and_history_commands(self) -> None:
        self.assertIn("*commandes*", msg.MENU_TEXT)
        self.assertIn("*historique*", msg.MENU_TEXT)
        self.assertIn("*sav*", msg.MENU_TEXT)

    def test_support_ticket_templates_are_rendered(self) -> None:
        created = msg.support_ticket_created(42)
        updated = msg.support_ticket_updated(42, "open")
        closed = msg.support_ticket_closed(42)

        self.assertIn("#42", created)
        self.assertIn("#42", updated)
        self.assertIn("open", updated)
        self.assertIn("#42", closed)


if __name__ == "__main__":
    unittest.main()
