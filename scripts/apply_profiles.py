"""Install this project's two profiles without copying credentials between them."""

import argparse
from datetime import datetime
from pathlib import Path
import re
import shutil
import subprocess

from dotenv import dotenv_values, set_key, unset_key
import yaml

ROOT = Path(__file__).resolve().parents[1]


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("operator", "channel", "main-user", "cx-user", "cx-bot"):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--dry-run", action="store_true")
    return p


def validate(args):
    for name, prefix in (("operator", "U"), ("channel", "[CG]"),
                         ("main_user", "U"), ("cx_user", "U"), ("cx_bot", "B")):
        if not re.fullmatch(prefix + r"[A-Z0-9]{8,}", getattr(args, name)):
            raise ValueError(f"Invalid Slack ID: {name}")
    if len({args.operator, args.main_user, args.cx_user}) != 3:
        raise ValueError("Operator, A and CX must be distinct Slack users")


def apply(args):
    validate(args)
    if args.dry_run:
        print("Validated: will configure main and cx, install the bridge, disable API fallback. No changes made.")
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for name in ("main", "cx"):
        folder = Path.home() / ".hermes/profiles" / name
        if not folder.exists():
            subprocess.run(["hermes", "profile", "create", name, "--no-alias", "--no-skills"], check=True)
        folder.chmod(0o700)
        backup = folder / f"config-backup-{stamp}"
        backup.mkdir(mode=0o700)
        for filename in ("config.yaml", "SOUL.md"):
            target = folder / filename
            if target.exists():
                shutil.copy2(target, backup / filename)
            shutil.copyfile(ROOT / "templates" / name / filename, target)
            target.chmod(0o600)
        config_path = folder / "config.yaml"
        config = yaml.safe_load(config_path.read_text())
        extra = config["platforms"]["slack"]["extra"]
        extra.update(allow_admin_from=[args.operator], group_allow_admin_from=[args.operator],
                     user_allowed_commands=["help", "whoami"], group_user_allowed_commands=["help", "whoami"])
        config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
        env = folder / ".env"
        if not env.exists():
            shutil.copyfile(ROOT / "templates" / name / ".env.example", env)
        env.chmod(0o600)
        values = {
            "SLACK_ALLOWED_USERS": args.operator + "," + (args.main_user if name == "cx" else args.cx_user),
            "SLACK_ALLOWED_CHANNELS": args.channel, "SLACK_HOME_CHANNEL": args.channel,
            "SLACK_ALLOW_ALL_USERS": "false", "GATEWAY_ALLOW_ALL_USERS": "false",
            "SLACK_ALLOW_BOTS": "mentions",
            "SLACK_REQUIRE_MENTION": "true", "SLACK_STRICT_MENTION": "true" if name == "cx" else "false",
        }
        if name == "main":
            values.update(CX_AGENT_USER_ID=args.cx_user, CX_AGENT_BOT_ID=args.cx_bot,
                          HUMAN_REVIEW_USER_ID=args.operator)
        else:
            values["MAIN_AGENT_USER_ID"] = args.main_user
        for key, value in values.items():
            set_key(env, key, value)
        if "OPENAI_API_KEY" in dotenv_values(env):
            unset_key(env, "OPENAI_API_KEY")
        if (folder / "auth.json").exists():
            (folder / "auth.json").chmod(0o600)
        destination = folder / "plugins/cx-thread-bridge"
        destination.parent.mkdir(exist_ok=True)
        shutil.copytree(ROOT / "plugins/cx-thread-bridge", destination,
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        print(f"Configured {name}. Credentials preserved in this profile. Services were not restarted.")


if __name__ == "__main__":
    apply(parser().parse_args())
