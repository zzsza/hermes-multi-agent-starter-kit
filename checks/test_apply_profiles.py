import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dotenv import dotenv_values
import yaml

spec = importlib.util.spec_from_file_location("setup", Path(__file__).resolve().parents[1] / "scripts/apply_profiles.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTest(unittest.TestCase):
    def args(self):
        return SimpleNamespace(operator="UHUMAN12345", channel="CCHANNEL123", main_user="UMAIN123456",
            cx_user="UCX12345678", cx_bot="BCX12345678", dry_run=False)

    def test_setup_preserves_credentials_and_limits_bots(self):
        with TemporaryDirectory() as temp, patch.object(Path, "home", return_value=Path(temp)):
            profiles = Path(temp) / ".hermes/profiles"
            for name in ("main", "cx"):
                folder = profiles / name
                folder.mkdir(parents=True)
                (folder / ".env").write_text(f"SLACK_BOT_TOKEN=fixture-{name}\nOPENAI_API_KEY=\n")
                (folder / "auth.json").write_text('{"fixture":"preserve"}')
            setup.apply(self.args())
            main = dotenv_values(profiles / "main/.env")
            cx = dotenv_values(profiles / "cx/.env")
            self.assertEqual(main["SLACK_BOT_TOKEN"], "fixture-main")
            self.assertEqual(cx["SLACK_BOT_TOKEN"], "fixture-cx")
            self.assertEqual(cx["SLACK_ALLOWED_USERS"], "UHUMAN12345,UMAIN123456")
            self.assertEqual(main["SLACK_ALLOWED_USERS"], "UHUMAN12345,UCX12345678")
            self.assertEqual(main["HUMAN_REVIEW_USER_ID"], "UHUMAN12345")
            self.assertEqual(cx["SLACK_ALLOW_BOTS"], "mentions")
            self.assertEqual(main["SLACK_ALLOW_BOTS"], "mentions")
            self.assertEqual(cx["MAIN_AGENT_USER_ID"], "UMAIN123456")
            self.assertNotIn("OPENAI_API_KEY", main)
            self.assertEqual((profiles / "cx/auth.json").read_text(), '{"fixture":"preserve"}')
            self.assertTrue((profiles / "main/plugins/cx-thread-bridge/__init__.py").exists())
            self.assertTrue((profiles / "cx/plugins/cx-thread-bridge/__init__.py").exists())
            for name in ("main", "cx"):
                config = yaml.safe_load((profiles / name / "config.yaml").read_text())
                self.assertEqual(config["fallback_providers"], [])
                extra = config["platforms"]["slack"]["extra"]
                self.assertEqual(extra["allow_admin_from"], ["UHUMAN12345"])
                self.assertEqual(extra["group_allow_admin_from"], ["UHUMAN12345"])

    def test_wildcards_and_shared_identity_rejected(self):
        args = self.args()
        args.operator = "*"
        with self.assertRaises(ValueError):
            setup.validate(args)
        args = self.args()
        args.cx_user = args.main_user
        with self.assertRaises(ValueError):
            setup.validate(args)

    def test_dry_run_makes_no_changes(self):
        args = self.args()
        args.dry_run = True
        with TemporaryDirectory() as temp, patch.object(Path, "home", return_value=Path(temp)):
            setup.apply(args)
            self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
