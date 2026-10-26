"""자료 정적 검사. 모델, Slack, 사용자 인증 파일에는 접근하지 않습니다."""

import copy
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def validate():
    for profile in ("main", "cx"):
        folder = ROOT / "templates" / profile
        config = yaml.safe_load((folder / "config.yaml").read_text())
        assert config["model"]["provider"] == "openai-codex"
        assert config["model"]["default"] == "gpt-6-astra"
        expected_slack = ["todo", "clarify", "cx_consult"] if profile == "main" else ["todo", "clarify", "cx_report"]
        assert config["platform_toolsets"] == {"cli": ["todo", "clarify"], "slack": expected_slack}
        assert config["plugins"]["enabled"] == ["cx-thread-bridge"]
        assert config["approvals"]["mode"] == "manual"
        assert config["approvals"]["cron_mode"] == "deny"
        assert config["command_allowlist"] == []
        assert config["terminal"]["backend"] == "docker"
        assert config["memory"]["memory_enabled"] is False
        assert config["memory"]["user_profile_enabled"] is False
        assert set(config["auxiliary"]) == {
            "vision", "web_extract", "compression", "session_search", "title_generation"
        }
        assert all(slot == {"provider": "codex", "model": "gpt-6-astra"}
                   for slot in config["auxiliary"].values())
        assert config["fallback_providers"] == []
        assert not config.get("fallback_model")
        slack = config["platforms"]["slack"]["extra"]
        assert config["platforms"]["slack"]["gateway_restart_notification"] is False
        assert slack == {
            "reply_in_thread": True, "require_mention": True,
            "strict_mention": profile == "cx", "free_response_channels": [],
            "allow_bots": "mentions",
            "allow_admin_from": [], "group_allow_admin_from": [],
            "user_allowed_commands": ["help", "whoami"], "group_user_allowed_commands": ["help", "whoami"]
        }
        env = dict(line.split("=", 1) for line in (folder / ".env.example").read_text().splitlines()
                   if line and not line.startswith("#"))
        assert all(env[key] == "" for key in (
            "SLACK_BOT_TOKEN", "SLACK_APP_TOKEN",
            "SLACK_HOME_CHANNEL", "SLACK_ALLOWED_CHANNELS"
        ))
        assert env["SLACK_ALLOWED_USERS"] == ""
        assert "OPENAI_API_KEY" not in env
        if profile == "main":
            assert env["HUMAN_REVIEW_USER_ID"] == ""
        else:
            assert env["MAIN_AGENT_USER_ID"] == ""
        assert env["SLACK_ALLOW_ALL_USERS"] == env["GATEWAY_ALLOW_ALL_USERS"] == "false"
        assert env["SLACK_ALLOW_BOTS"] == "mentions"
        assert env["SLACK_REQUIRE_MENTION"] == "true"
        assert env["SLACK_STRICT_MENTION"] == ("true" if profile == "cx" else "false")

        original = json.loads((ROOT / "manifests" / f"{profile}.generated.json").read_text())
        pilot = json.loads((ROOT / "manifests" / f"{profile}.pilot.json").read_text())
        expected = copy.deepcopy(original)
        expected["features"].pop("slash_commands")
        expected["oauth_config"]["scopes"]["bot"].remove("commands")
        assert pilot == expected, "파일럿 매니페스트에 의도하지 않은 변경이 있습니다."
        display = pilot["display_information"]["name"]
        assert isinstance(display, str) and display.strip(), "직원 표시 이름이 비어 있습니다."
        assert pilot["features"]["bot_user"]["display_name"] == display, "앱과 봇 표시 이름이 다릅니다."
        assert {"channels:history", "groups:history", "files:read"}.issubset(
            pilot["oauth_config"]["scopes"]["bot"])
        assert {"app_mention", "message.channels", "message.groups", "message.im"}.issubset(
            pilot["settings"]["event_subscriptions"]["bot_events"])
        assert pilot["settings"]["socket_mode_enabled"] is True
        assert pilot["settings"]["interactivity"]["is_enabled"] is True
        home = pilot["features"]["app_home"]
        assert home["messages_tab_enabled"] is True
        assert home["messages_tab_read_only_enabled"] is False

    forbidden = re.compile(r"(?:xox[baprs]-[A-Za-z0-9-]{12,}|xapp-[A-Za-z0-9-]{12,}|sk-[A-Za-z0-9_-]{20,})")
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {"__pycache__", ".git", "private"} for part in path.relative_to(ROOT).parts):
            continue
        assert path.name not in {".env", "auth.json", "state.json"} and not path.name.endswith("-slack-state.json"), "자료 폴더에 인증 또는 환경 상태 파일이 있습니다."
        if path.suffix not in {".md", ".yaml", ".json", ".template", ".example", ".py"}:
            continue
        content = path.read_text()
        assert not forbidden.search(content), "실제 인증값으로 의심되는 문자열이 있습니다."
        if path.suffix == ".md":
            assert not any(char in content for char in "\u00b7\u318d\u2027\u2014"), "문장 구분 기호를 확인하세요."
            assert not re.search(r"/Users/[^/\s]+|https?://(?!api\.slack\.com(?:/|$))[^/\s]+\.slack\.com(?:/|\b)", content), "개인 경로나 워크스페이스 링크가 있습니다."
            assert not re.search(r"(?<![A-Z0-9_])[UTACBGD][A-Z0-9]{8,}(?![A-Z0-9_])", content), "문서에 실제 Slack 식별자로 보이는 값이 있습니다."
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)]+)\)", content):
                if not re.match(r"[a-z]+://", target) and not target.startswith("#"):
                    assert (path.parent / target.split("#")[0]).exists(), "문서 링크 대상이 없습니다."
    assert not list((ROOT / "templates").rglob("SKILL.md")), "미완성 스킬이 활성 파일 이름을 사용합니다."
    print("PASS: 두 프로필 설정, 비밀값 없는 환경 양식, 매니페스트, 스킬 비활성, 문서 링크")


if __name__ == "__main__":
    validate()
