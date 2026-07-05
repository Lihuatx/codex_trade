import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from okx_quant.config import load_env_file


class ConfigTests(unittest.TestCase):
    def test_load_env_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.test"
            path.write_text("FOO=bar\nQUOTED='baz'\n# comment\n", encoding="utf-8")

            old_foo = os.environ.get("FOO")
            old_quoted = os.environ.get("QUOTED")
            try:
                load_env_file(path)
                self.assertEqual(os.environ["FOO"], "bar")
                self.assertEqual(os.environ["QUOTED"], "baz")
            finally:
                if old_foo is None:
                    os.environ.pop("FOO", None)
                else:
                    os.environ["FOO"] = old_foo
                if old_quoted is None:
                    os.environ.pop("QUOTED", None)
                else:
                    os.environ["QUOTED"] = old_quoted


if __name__ == "__main__":
    unittest.main()

