"""No network: thread confinement, trusted replies, one consultation, failures."""

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path.home() / ".hermes/hermes-agent"))
spec = importlib.util.spec_from_file_location("bridge", Path(__file__).resolve().parents[1] / "plugins/cx-thread-bridge/__init__.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class FakeSlack:
    def __init__(self, mode="normal"):
        self.mode = mode
        self.sent = []

    def chat_postMessage(self, **kwargs):
        self.sent.append(kwargs)
        if self.mode == "send_error":
            raise RuntimeError("sensitive value that must never leave this exception")
        return {"ts": "123.002"}

    def conversations_replies(self, **kwargs):
        text = self.sent[0]["text"]
        rid = text.split("CX 확인 요청 [")[1].split("]")[0]
        trusted = {"user": "UCX12345678", "bot_id": "BCX12345678",
                   "thread_ts": "123.001", "ts": "123.003",
                   "text": f"CX 확인 결과 [{rid}]\nCX verified answer\nCX 확인 완료 [{rid}]"}
        spoof = dict(trusted, user="UOTHER12345")
        stale = dict(trusted, text="CX 확인 결과 [old]\nstale\nCX 확인 완료 [old]")
        partial = dict(trusted, text=f"CX 확인 결과 [{rid}]\npartial")
        return {"messages": [spoof, stale, partial] + ([] if self.mode == "timeout" else [trusted])}


class BridgeTest(unittest.TestCase):
    def setUp(self):
        bridge._receipts.clear()
        self.context = {"HERMES_SESSION_PLATFORM": "slack", "HERMES_SESSION_CHAT_ID": "C1234567890",
                        "HERMES_SESSION_THREAD_ID": "123.001", "HERMES_SESSION_USER_ID": "UHUMAN12345"}
        self.env = patch.dict(os.environ, {"SLACK_ALLOWED_USERS": "UHUMAN12345",
            "SLACK_ALLOWED_CHANNELS": "C1234567890", "CX_AGENT_USER_ID": "UCX12345678",
            "CX_AGENT_BOT_ID": "BCX12345678", "SLACK_BOT_TOKEN": "fake-for-test"})
        self.env.start()
        self.ctx = patch.object(bridge, "get_session_env", side_effect=lambda key: self.context.get(key, ""))
        self.ctx.start()

    def tearDown(self):
        self.ctx.stop()
        self.env.stop()

    def call(self, client, question="CS question"):
        with patch.object(bridge, "WebClient", return_value=client):
            return json.loads(bridge.consult_cx({"question": question}, task_id="turn-1"))

    def test_trusted_complete_reply_and_thread(self):
        client = FakeSlack()
        result = self.call(client, "CS question <!channel> <@UOTHER>")
        self.assertEqual(result["answer"], "CX verified answer")
        self.assertEqual(client.sent[0]["channel"], "C1234567890")
        self.assertEqual(client.sent[0]["thread_ts"], "123.001")
        self.assertNotIn("<!channel>", client.sent[0]["text"])
        self.assertNotIn("<@UOTHER>", client.sent[0]["text"])

    def test_quotes_remain_readable(self):
        client = FakeSlack()
        self.call(client, "고객이 '환불'을 요청했습니다.")
        self.assertIn("'환불'", client.sent[0]["text"])
        self.assertNotIn("&#x27;", client.sent[0]["text"])

    def test_repeated_call_sends_once_and_new_question_denied(self):
        client = FakeSlack()
        self.assertEqual(self.call(client), self.call(client))
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(self.call(client, "another question")["error"], "one_cx_consultation_per_turn")

    def test_unknown_send_is_not_retried_or_exposed(self):
        client = FakeSlack("send_error")
        first = self.call(client)
        self.assertEqual(first, self.call(client))
        self.assertEqual(len(client.sent), 1)
        self.assertNotIn("sensitive", json.dumps(first))

    def test_wrong_channel_user_platform_and_missing_thread_fail_closed(self):
        for key, value in [("HERMES_SESSION_CHAT_ID", "COTHER12345"),
                           ("HERMES_SESSION_USER_ID", "UBOT1234567"),
                           ("HERMES_SESSION_PLATFORM", "cli"),
                           ("HERMES_SESSION_THREAD_ID", "")]:
            with self.subTest(key=key):
                old = self.context[key]
                self.context[key] = value
                client = FakeSlack()
                self.assertEqual(self.call(client)["error"], "authorized_slack_thread_required")
                self.assertEqual(client.sent, [])
                self.context[key] = old

    def test_timeout(self):
        with patch.object(bridge, "WAIT_SECONDS", 0):
            client = FakeSlack("timeout")
            self.assertEqual(self.call(client)["error"], "cx_timeout_do_not_resend")
            self.call(client)
            self.assertEqual(len(client.sent), 1)

    def test_human_review_fixed_recipient_thread_and_dedup(self):
        client = FakeSlack()
        with patch.dict(os.environ, {"HUMAN_REVIEW_USER_ID": "UREVIEW1234"}), patch.object(bridge, "WebClient", return_value=client):
            args = {"reason": "missing_policy", "question": "정책이 필요합니다. <!channel> <@UOTHER>"}
            first = json.loads(bridge.request_human_review(args, task_id="turn-1"))
            second = json.loads(bridge.request_human_review(args, task_id="turn-1"))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "human_review_requested")
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(client.sent[0]["thread_ts"], "123.001")
        self.assertTrue(client.sent[0]["text"].startswith("<@UREVIEW1234>"))
        self.assertNotIn("<!channel>", client.sent[0]["text"])
        self.assertNotIn("<@UOTHER>", client.sent[0]["text"])

    def test_timeout_automatically_requests_human_once(self):
        client = FakeSlack("timeout")
        with patch.dict(os.environ, {"HUMAN_REVIEW_USER_ID": "UREVIEW1234"}), patch.object(bridge, "WAIT_SECONDS", 0):
            result = self.call(client)
            self.call(client)
        self.assertEqual(result["human_review"]["status"], "human_review_requested")
        self.assertEqual(len(client.sent), 2)

    def test_review_missing_context_fails_closed(self):
        self.context["HERMES_SESSION_THREAD_ID"] = ""
        client = FakeSlack()
        with patch.dict(os.environ, {"HUMAN_REVIEW_USER_ID": "UREVIEW1234"}), patch.object(bridge, "WebClient", return_value=client):
            result = json.loads(bridge.request_human_review({"reason": "approval_required", "question": "확인 요청"}, task_id="turn-1"))
        self.assertIn("error", result)
        self.assertEqual(client.sent, [])

    def test_cx_can_report_to_fixed_main_once_in_current_thread(self):
        client = FakeSlack()
        with patch.dict(os.environ, {"MAIN_AGENT_USER_ID": "UMAIN123456"}), patch.object(bridge, "WebClient", return_value=client):
            args = {"reason": "conflicting_information", "summary": "충돌 확인 요청 <!channel> <@UOTHER>"}
            first = json.loads(bridge.report_to_main(args, task_id="turn-1"))
            second = json.loads(bridge.report_to_main(args, task_id="turn-1"))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "reported_to_main")
        self.assertEqual(len(client.sent), 1)
        self.assertTrue(client.sent[0]["text"].startswith("<@UMAIN123456> CX 조율 보고 ["))
        self.assertEqual(client.sent[0]["thread_ts"], "123.001")
        self.assertNotIn("<!channel>", client.sent[0]["text"])
        self.assertNotIn("<@UOTHER>", client.sent[0]["text"])

    def test_a_cx_requests_cannot_bounce_back_in_either_direction(self):
        client = FakeSlack()
        with patch.dict(os.environ, {"MAIN_AGENT_USER_ID": "UMAIN123456", "SLACK_ALLOWED_USERS": "UHUMAN12345,UMAIN123456"}), patch.object(bridge, "WebClient", return_value=client):
            self.context["HERMES_SESSION_USER_ID"] = "UMAIN123456"
            self.assertEqual(json.loads(bridge.report_to_main(
                {"reason": "missing_policy", "summary": "test"}, task_id="turn-1"))["error"],
                "main_requested_work_cannot_be_reported_back")
        self.context["HERMES_SESSION_USER_ID"] = "UCX12345678"
        self.assertEqual(self.call(client)["error"], "cx_report_cannot_be_sent_back_to_cx")
        self.assertEqual(client.sent, [])

    def test_report_unauthorized_context_and_unknown_send(self):
        client = FakeSlack("send_error")
        with patch.dict(os.environ, {"MAIN_AGENT_USER_ID": "UMAIN123456"}), patch.object(bridge, "WebClient", return_value=client):
            args = {"reason": "needs_coordination", "summary": "test"}
            self.context["HERMES_SESSION_CHAT_ID"] = "COTHER12345"
            self.assertIn("error", json.loads(bridge.report_to_main(args, task_id="turn-1")))
            self.assertEqual(client.sent, [])
            self.context["HERMES_SESSION_CHAT_ID"] = "C1234567890"
            first = bridge.report_to_main(args, task_id="turn-1")
            self.assertEqual(first, bridge.report_to_main(args, task_id="turn-1"))
            self.assertEqual(len(client.sent), 1)
            self.assertNotIn("sensitive", first)


if __name__ == "__main__":
    unittest.main()
