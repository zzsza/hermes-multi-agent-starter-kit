"""Bounded A/CX coordination in the authorized current Slack thread."""

import hashlib
import html
import json
import os
import re
import threading
import time
import uuid

from gateway.session_context import get_session_env
from slack_sdk import WebClient

WAIT_SECONDS = 120
POLL_SECONDS = 4
_receipts = {}
_lock = threading.Lock()


def _result(**data):
    return json.dumps(data, ensure_ascii=False)


def _thread_context(task_id):
    channel = get_session_env("HERMES_SESSION_CHAT_ID")
    thread = get_session_env("HERMES_SESSION_THREAD_ID")
    user = get_session_env("HERMES_SESSION_USER_ID")
    users = {v.strip() for v in os.environ.get("SLACK_ALLOWED_USERS", "").split(",")}
    channels = {v.strip() for v in os.environ.get("SLACK_ALLOWED_CHANNELS", "").split(",")}
    if (get_session_env("HERMES_SESSION_PLATFORM") != "slack" or not task_id
            or not channel or channel not in channels or not user or user not in users
            or "*" in users or "*" in channels
            or not re.fullmatch(r"\d+\.\d+", thread or "")):
        return None
    return channel, thread


def request_human_review(args, **kwargs):
    """Tag only the configured reviewer, only in the authorized current thread."""
    task_id = kwargs.get("task_id")
    context = _thread_context(task_id)
    reviewer = os.environ.get("HUMAN_REVIEW_USER_ID", "")
    reasons = {"cx_unavailable": "CX 응답 확인 실패", "missing_policy": "정책 또는 근거 부족",
               "conflicting_information": "정보 충돌", "approval_required": "사람 승인 필요",
               "out_of_scope": "직접 처리할 수 없는 업무"}
    reason = args.get("reason")
    question = args.get("question")
    if (context is None or not re.fullmatch(r"U[A-Z0-9]{8,}", reviewer)
            or reason not in reasons or not isinstance(question, str)
            or not 1 <= len(question.strip()) <= 2000):
        return _result(error="authorized_thread_reviewer_and_question_required")
    channel, thread = context
    key = (channel, thread, str(task_id), "human")
    with _lock:
        now = time.monotonic()
        for old in [k for k, v in _receipts.items() if v["expires"] < now]:
            del _receipts[old]
        if key in _receipts:
            return _receipts[key]["result"]
        if len(_receipts) >= 128:
            return _result(error="review_capacity_reached")
        receipt = {"expires": now + 600, "result": _result(error="review_in_progress_do_not_resend")}
        _receipts[key] = receipt
    try:
        client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"), timeout=10, retry_handlers=[])
        sent = client.chat_postMessage(channel=channel, thread_ts=thread,
            client_msg_id=uuid.uuid4().hex, unfurl_links=False, unfurl_media=False,
            text=(f"<@{reviewer}> 확인이 필요합니다: {reasons[reason]}\n"
                  f"{html.escape(question.strip(), quote=False)}\n"
                  "이 스레드에 판단 또는 추가 정보를 남겨주세요. 확인 전에는 해당 작업을 진행하지 않겠습니다."))
        output = _result(status="human_review_requested", reviewer=reviewer, message_ts=sent["ts"])
    except Exception:
        output = _result(error="human_review_send_unknown_do_not_resend")
    with _lock:
        receipt["result"] = output
    return output


def consult_cx(args, **kwargs):
    """Only a human-triggered main turn can ask the configured CX bot once."""
    question = args.get("question")
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 4000:
        return _result(error="question_must_be_1_to_4000_characters")
    question = question.strip()
    task_id = kwargs.get("task_id")
    context = _thread_context(task_id)
    cx_user = os.environ.get("CX_AGENT_USER_ID", "")
    cx_bot = os.environ.get("CX_AGENT_BOT_ID", "")
    if get_session_env("HERMES_SESSION_USER_ID") == cx_user:
        return _result(error="cx_report_cannot_be_sent_back_to_cx")
    if context is None:
        return _result(error="authorized_slack_thread_required")
    channel, thread = context
    if not re.fullmatch(r"U[A-Z0-9]{8,}", cx_user) or not re.fullmatch(r"B[A-Z0-9]{8,}", cx_bot):
        return _result(error="cx_identity_not_configured")

    # One consultation per agent turn. Cache errors too: an uncertain send must not retry.
    key = (channel, thread, str(task_id))
    fingerprint = hashlib.sha256(question.encode()).hexdigest()
    now = time.monotonic()
    with _lock:
        for old in [k for k, v in _receipts.items() if v["expires"] < now]:
            del _receipts[old]
        if key in _receipts:
            old = _receipts[key]
            if old["fingerprint"] != fingerprint:
                return _result(error="one_cx_consultation_per_turn")
            return old["result"]
        if len(_receipts) >= 128:
            return _result(error="consultation_capacity_reached")
        receipt = {"fingerprint": fingerprint, "expires": now + 600,
                   "result": _result(error="consultation_in_progress_do_not_resend")}
        _receipts[key] = receipt

    request_id = uuid.uuid4().hex
    reference = request_id[:12]
    header = f"CX 확인 결과 [{reference}]"
    footer = f"CX 확인 완료 [{reference}]"
    posted = False
    try:
        client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"), timeout=10, retry_handlers=[])
        sent = client.chat_postMessage(
            channel=channel, thread_ts=thread, client_msg_id=request_id,
            text=f"<@{cx_user}> CX 확인 요청 [{reference}]\n{html.escape(question, quote=False)}",
            unfurl_links=False, unfurl_media=False,
        )
        posted = True
        deadline = time.monotonic() + WAIT_SECONDS
        output = _result(error="cx_timeout_do_not_resend", request_id=request_id)
        while time.monotonic() < deadline:
            replies = client.conversations_replies(channel=channel, ts=thread,
                oldest=sent["ts"], inclusive=False, limit=100)
            for message in replies.get("messages", []):
                text = message.get("text", "").strip()
                if (message.get("user") == cx_user and message.get("bot_id") == cx_bot
                        and message.get("thread_ts") == thread
                        and text.startswith(header) and text.endswith(footer)):
                    answer = text[len(header):-len(footer)].strip()
                    if answer:
                        output = _result(status="answered", request_id=request_id,
                            reply_ts=message["ts"], answer=answer[:12000])
                        break
            if json.loads(output).get("status") == "answered":
                break
            if replies.get("has_more") or replies.get("response_metadata", {}).get("next_cursor"):
                output = _result(error="thread_read_limit_reached_do_not_resend", request_id=request_id)
                break
            time.sleep(POLL_SECONDS)
    except Exception:
        # Exception strings can include request URLs or credentials. Never return them.
        output = _result(error="cx_reply_unavailable" if posted else "send_status_unknown_do_not_resend",
                         request_id=request_id)
    if "error" in json.loads(output):
        review = request_human_review({"reason": "cx_unavailable",
            "question": "CX의 완성된 답변을 확인하지 못했습니다. 재전송하지 않고 담당자 확인을 기다립니다.\n"
                        + question[:1200]}, **kwargs)
        data = json.loads(output)
        data["human_review"] = json.loads(review)
        output = _result(**data)
    with _lock:
        receipt["result"] = output
    return output


def report_to_main(args, **kwargs):
    """A human-triggered CX turn may report to A without waiting or bouncing back."""
    task_id = kwargs.get("task_id")
    context = _thread_context(task_id)
    main_user = os.environ.get("MAIN_AGENT_USER_ID", "")
    if not re.fullmatch(r"U[A-Z0-9]{8,}", main_user) or context is None:
        return _result(error="authorized_thread_and_main_identity_required")
    if get_session_env("HERMES_SESSION_USER_ID") == main_user:
        return _result(error="main_requested_work_cannot_be_reported_back")
    reasons = {"needs_coordination": "다른 업무와 조율 필요", "missing_policy": "정책 또는 근거 부족",
               "conflicting_information": "정보 충돌", "approval_required": "사람 승인 필요",
               "out_of_scope": "CX 처리 범위 밖"}
    reason, summary = args.get("reason"), args.get("summary")
    if reason not in reasons or not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 4000:
        return _result(error="valid_reason_and_summary_required")
    channel, thread = context
    key = (channel, thread, str(task_id), "report")
    with _lock:
        now = time.monotonic()
        for old in [k for k, v in _receipts.items() if v["expires"] < now]:
            del _receipts[old]
        if key in _receipts:
            return _receipts[key]["result"]
        if len(_receipts) >= 128:
            return _result(error="report_capacity_reached")
        receipt = {"expires": now + 600, "result": _result(error="report_in_progress_do_not_resend")}
        _receipts[key] = receipt
    reference = uuid.uuid4().hex[:12]
    try:
        client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"), timeout=10, retry_handlers=[])
        sent = client.chat_postMessage(channel=channel, thread_ts=thread,
            client_msg_id=uuid.uuid4().hex, unfurl_links=False, unfurl_media=False,
            text=(f"<@{main_user}> CX 조율 보고 [{reference}]\n사유: {reasons[reason]}\n"
                  f"{html.escape(summary.strip(), quote=False)}\n"
                  "A가 이 보고를 검토해 직접 정리하거나 담당자 판단을 요청해 주세요. "
                  "이 보고를 CX에게 다시 배정하지 마세요."))
        output = _result(status="reported_to_main", reference=reference, message_ts=sent["ts"])
    except Exception:
        output = _result(error="main_report_send_unknown_do_not_resend")
    with _lock:
        receipt["result"] = output
    return output


def register(ctx):
    if os.environ.get("MAIN_AGENT_USER_ID"):
        ctx.register_tool(name="report_to_main", toolset="cx_report",
            description="Report a CX finding to the fixed main agent in this thread.",
            schema={"name": "report_to_main", "description": (
                "사람이 CX에게 직접 요청한 업무를 검토하다 다른 업무와 조율, 정보 충돌, 정책 확인, "
                "승인이 필요해진 경우 실제 A에게 현재 Slack 스레드에서 보고합니다. "
                "현재 상황, 확인한 사실과 미확인 사항, A가 결정할 질문을 포함하세요. "
                "한 처리에 한 번만 보고하며 A가 맡긴 업무를 다시 A에게 보내는 용도로 쓸 수 없습니다."),
                "parameters": {"type": "object", "properties": {
                    "reason": {"type": "string", "enum": ["needs_coordination", "missing_policy",
                        "conflicting_information", "approval_required", "out_of_scope"]},
                    "summary": {"type": "string", "maxLength": 4000}},
                    "required": ["reason", "summary"], "additionalProperties": False}},
            handler=report_to_main,
            check_fn=lambda: bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("MAIN_AGENT_USER_ID")))
        return
    ctx.register_tool(
        name="consult_cx", toolset="cx_consult",
        description="Ask the actual CX agent in the current Slack thread.",
        schema={"name": "consult_cx", "description": (
            "고객 문의, CS/CX 사례, 고객 응대 정보가 필요한 경우 실제 별도 CX 에이전트에게 "
            "현재 Slack 스레드에서 질문하고 답을 기다립니다. 특정 스킬을 대신 수행하는 도구가 아닙니다. "
            "한 요청에서 한 번만 호출할 수 있습니다. 고객 발송과 데이터 변경은 요청하지 마세요. "
            "오류가 나면 재호출하지 말고 확인 불가로 보고하세요."),
            "parameters": {"type": "object", "properties": {
                "question": {"type": "string", "description": "CX에 필요한 배경을 포함한 구체적인 질문", "maxLength": 4000}},
                "required": ["question"], "additionalProperties": False}},
        handler=consult_cx,
        check_fn=lambda: bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("CX_AGENT_USER_ID")),
    )
    ctx.register_tool(name="request_human_review", toolset="cx_consult",
        description="Ask the fixed human reviewer to clarify or approve in this Slack thread.",
        schema={"name": "request_human_review", "description": (
            "판단에 필요한 정책이 없거나 정보가 충돌하거나 사람 승인이 필요한 경우 현재 스레드에서 "
            "설정된 담당자를 직접 태그합니다. 한 처리에서 한 번만 알리고 답변을 기다리세요. "
            "반환된 전송 결과를 확인하고 실제 태그가 성공한 경우에만 확인 요청했다고 말하세요."),
            "parameters": {"type": "object", "properties": {
                "reason": {"type": "string", "enum": ["cx_unavailable", "missing_policy",
                    "conflicting_information", "approval_required", "out_of_scope"]},
                "question": {"type": "string", "description": "현재 상황과 사람이 판단하거나 제공해야 할 정보", "maxLength": 2000}},
                "required": ["reason", "question"], "additionalProperties": False}},
        handler=request_human_review,
        check_fn=lambda: bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("HUMAN_REVIEW_USER_ID")))
