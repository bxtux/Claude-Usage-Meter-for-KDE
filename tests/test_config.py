from pathlib import Path
import tempfile
import unittest

from claude_usage_meter.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_creates_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config = load_config(config_path)

            self.assertTrue(config_path.exists())
            self.assertEqual(config.refresh_seconds, 120)
            self.assertEqual(config.threshold_percent, 80)


if __name__ == "__main__":
    unittest.main()
