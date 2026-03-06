import ast
from pathlib import Path
import unittest


class MainSourceGuardTests(unittest.TestCase):
    def test_main_imports_db_when_internal_worker_endpoints_use_it(self) -> None:
        source_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))

        imported_names: set[str] = set()
        db_attribute_uses = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name.split(".")[-1])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "db":
                    db_attribute_uses += 1

        self.assertGreater(db_attribute_uses, 0, "main.py no longer uses db.*; update this guard")
        self.assertIn("db", imported_names, "main.py uses db.* but does not import db")


if __name__ == "__main__":
    unittest.main()
