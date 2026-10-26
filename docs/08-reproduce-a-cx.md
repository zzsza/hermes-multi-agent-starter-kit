# 다른 Mac에서 A와 CX 재현하기

먼저 [SETUP.md](../SETUP.md)에서 대상 환경과 계정, 설치할 도구, Slack 워크스페이스와 테스트 채널을 확인합니다. 이 문서에는 개인 환경의 기본 ID가 없습니다.

최신 구조는 **사람 → A → 실제 CX → A**, 또는 **사람 → CX → A 조율 보고**이며, 모든 중간 통신과 최종 회신은 원래 Slack 스레드입니다. API fallback은 완전히 비활성화합니다. 기본 `delegate_task`나 칸반을 통한 새 에이전트 생성은 사용하지 않습니다. 고정된 두 개의 Hermes 프로필과 Slack 앱만 연결합니다.

## 1. 옮길 것과 옮기지 않을 것

이 자료 폴더 전체를 대상 Mac에 옮깁니다. 필수 파일은 `templates/`, `plugins/cx-thread-bridge/`, `scripts/apply_profiles.py`, `checks/`, `manifests/`, 이 문서와 `USAGE.md`입니다.

`.env`, `auth.json`, state.json과 Slack 상태 JSON, 세션 DB와 로그, private 폴더와 브라우저 상태는 옮기지 않습니다. 대상 Mac에서 새로 인증하고 토큰은 해당 프로필 `.env`에만 입력합니다. 환경 식별자는 사용자에게 대상을 질문한 뒤 새로 확인합니다.

동일한 Slack 앱을 다른 컴퓨터로 이전하는 경우에는 이전 Mac의 두 서비스를 먼저 중지합니다. 동일 앱의 Socket Mode 연결을 두 Mac에서 동시에 운영하면 이벤트가 어느 컴퓨터로 갈지 불명확해집니다.

```sh
hermes -p main gateway stop
hermes -p cx gateway stop
```

## 2. 설치와 버전

검증한 설치는 Hermes v0.13.0, source commit `8c6b0c9ecd`, 전용 Python 3.11.13입니다. 새 Hermes 버전으로 설치하면 같은 코드라고 가정하지 말고 아래 테스트를 다시 실행합니다.

```sh
uname -srm
command -v hermes
hermes --version
hermes profile list
hermes doctor
```

없을 때는 [공식 installer](https://hermes-agent.nousresearch.com/docs/getting-started/installation)를 사용합니다.

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

검증에 사용한 source 설치의 Python 예시는 `~/.hermes/hermes-agent/venv/bin/python`입니다. 아래 명령은 이 설치 경로 기준입니다. 실제 설치 형태가 다르면 `hermes --version`이 표시하는 설치 환경의 Python으로 바꿉니다. 시스템 Python에 패키지를 섞어 설치하지 않습니다.

Slack 모듈이 없을 때는 해당 Hermes 버전의 `pyproject.toml`에 있는 Slack 의존성을 설치합니다. 검증 버전에서는 다음과 같습니다.

```sh
uv pip install --python "$HOME/.hermes/hermes-agent/venv/bin/python" \
  'slack-bolt==1.27.0' 'slack-sdk==3.40.1' 'aiohttp==3.13.3'
```

## 3. 두 프로필과 로그인

같은 이름이 이미 있으면 기존 용도를 먼저 확인합니다. 기존 기본 프로필은 건드리지 않습니다.

```sh
hermes profile create main --no-alias --no-skills
hermes profile create cx --no-alias --no-skills
hermes -p main auth add openai-codex --no-browser
hermes -p cx auth add openai-codex --no-browser
```

사용할 ChatGPT 계정과 플랜을 확인하고 각 로그인은 운영자가 직접 승인합니다. 같은 계정을 사용하는 경우에도 두 프로필은 각각 별도의 OAuth 세션을 발급합니다. 해당 계정의 모델 접근과 사용 한도는 별도로 확인합니다. `--clone`만으로 `auth.json`이 복제되는 것은 아니며, 인증 파일을 복사해 공유하는 방식의 갱신 안정성은 검증하지 않았습니다.

로그인 후 각 프로필의 모델에서 `openai-codex`, 목표 모델 `gpt-6-astra` 접근을 확인합니다. 이전 개발 시험의 source 설치에서 주 모델과 제목 생성, 압축 호출은 실제 성공했습니다. 새 계정이나 버전의 모델 권한까지 보장하는 것은 아닙니다.

## 4. Slack 앱 두 개

메인 직원과 CX 직원의 Slack 표시 이름을 한 번 질문합니다. `Hermes A`, `Hermes CX`는 선택 가능한 기본 예시이며 확정값이 아닙니다. 이미 답한 이름은 다시 묻지 않습니다. 확정한 이름을 각 역할의 generated.json과 pilot.json의 `display_information.name`, `features.bot_user.display_name`에 동일하게 반영하고, SOUL 제목과 자기소개, 사용 안내의 멘션 예시에도 반영합니다. 내부 프로필 main과 cx는 그대로 유지합니다.

[Slack 앱 관리](https://api.slack.com/apps)에서 확정한 이름으로 앱 두 개를 생성합니다. `From a manifest`로 해당 `main.pilot.json`, `cx.pilot.json`을 사용합니다. 앱 두 개 모두 동일한 대상 워크스페이스에 설치합니다.

각 앱에서 Socket Mode를 켜고 `connections:write`의 app token을 만듭니다. 설치된 bot token과 app token을 정확히 해당 프로필의 `.env`에 입력합니다.

```text
main/.env: A 앱의 SLACK_BOT_TOKEN과 SLACK_APP_TOKEN
cx/.env: CX 앱의 SLACK_BOT_TOKEN과 SLACK_APP_TOKEN
```

한 앱의 토큰을 두 프로필에 재사용하지 않습니다. API 키는 입력하지 않습니다.

Messages Tab ON, read only OFF를 확인합니다. `app_mention`, `message.channels`, `message.groups`, `message.im` 구독과 history, files scopes를 대조합니다. 스레드를 읽는 A의 bot token에는 채널 history 권한이 필요합니다.

운영자가 테스트 채널에 **두 봇을 모두 초대**합니다. 채널 이름 대신 channel ID, 운영자와 봇 이름 대신 Member ID를 수집합니다. CX는 bot ID도 필요합니다. bot token으로 `auth.test`를 호출하면 `user_id`, `bot_id`, `team_id`를 확인할 수 있습니다. 출력할 때는 토큰 자체나 전체 인증 파일을 찍지 않습니다.

확인할 식별자는 운영자 Member ID, 테스트 channel ID, A Member ID, CX Member ID와 CX bot ID입니다. 새로 생성하거나 이전하기로 확인한 앱에서 수집합니다. 사람 조율 담당자는 기본적으로 운영자를 사용하되 동일 담당자인지 질문합니다. 다른 담당자라면 적용 뒤 main 허용 목록과 HUMAN_REVIEW_USER_ID에 함께 반영합니다.

## 5. 설정과 플러그인 적용

이 폴더로 이동한 뒤 사용자에게 확인한 실제 ID로 검증합니다. 아래 대문자 표시값을 실제 ID로 바꾼 뒤 실행합니다. 표시값 그대로는 ID 형식 검사에서 거부됩니다. 비어 있는 템플릿으로 서비스를 시작하지 않습니다.

```sh
~/.hermes/hermes-agent/venv/bin/python scripts/apply_profiles.py \
  --operator OPERATOR_MEMBER_ID --channel TEST_CHANNEL_ID \
  --main-user A_MEMBER_ID --cx-user CX_MEMBER_ID --cx-bot CX_BOT_ID \
  --dry-run
```

문제가 없으면 마지막 `--dry-run`을 빼고 실행합니다. 이 스크립트는 다음 작업을 합니다.

- 기존 `config.yaml`, `SOUL.md`를 프로필 내부의 날짜별 폴더에 백업한 뒤 이 자료의 구성으로 교체합니다.
- 각 프로필의 기존 Slack 토큰과 OAuth는 유지합니다. 프로필 간 인증을 복사하지 않습니다.
- A의 요청자는 운영자와 CX, CX의 요청자는 운영자와 A로 제한합니다.
- 두 프로필 모두 허용된 상대 봇이 실제 멘션한 메시지만 봇 이벤트로 받습니다. 일반 CX 확인 결과는 A를 멘션하지 않아 새 실행을 만들지 않습니다.
- CX에는 `strict_mention: true`, A에는 `strict_mention: false`를 적용합니다.
- 두 프로필에 `cx-thread-bridge` 플러그인을 설치합니다. main의 `cx_consult` 묶음은 `consult_cx`, `request_human_review`, cx의 `cx_report` 묶음은 `report_to_main`만 제공합니다. cx 환경에 `MAIN_AGENT_USER_ID`를 설정합니다.
- 사람 조율 담당자 `HUMAN_REVIEW_USER_ID`를 운영자로 설정하고 DM과 채널의 관리자 명령 권한을 운영자로 제한합니다.
- 서비스 시작과 종료의 홈 채널 알림을 끕니다.
- fallback 목록을 비우고 OpenAI API 키 항목을 제거합니다.
- 서비스는 자동 재시작하지 않습니다. 토큰 파일은 `600`, 프로필은 `700`입니다.

프로필을 재적용하면 SOUL도 이 자료의 내용으로 교체됩니다. 운영자가 이미 수정한 역할 설명과 스킬 지침은 먼저 자료에 반영하거나 백업에서 비교합니다.

## 6. 로컬 검사와 서비스

```sh
~/.hermes/hermes-agent/venv/bin/python checks/validate_templates.py
~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s checks -p 'test_*.py'
hermes -p cx gateway install
hermes -p main gateway install
hermes -p cx gateway status
hermes -p main gateway status
hermes gateway list
```

macOS의 이 launchd 서비스는 로그인한 사용자 세션에서 동작합니다. 최종 Mac mini에서는 재부팅 후 사용자 로그인, 서비스 복구와 절전 설정을 직접 검증합니다. 자동 로그인이 필요한지는 장비의 운영 방식과 보안 정책에 따라 별도로 결정합니다.

이미 설치된 서비스를 바꿨다면 프로필별 `gateway restart`로 새 설정을 읽힙니다. 기존 프로세스에 설정 파일만 복사한 상태로 검증하지 않습니다. `gateway run`을 별도로 띄워 중복 실행하지 않습니다.

## 7. 스레드 동작 검사

운영자가 테스트 채널에서 **A만** 멘션해 CS 관련 확인을 요청합니다. CX를 직접 부르라고 지시하지 않아도 A가 판단해 호출하는지 확인합니다.

```text
@Hermes A 고객이 배송 지연 때문에 환불을 원한다고 했어. 정책 자료는 아직 없어. 답변 전에 확인할 정보와 처리 순서를 알려줘. 실제 발송과 환불은 하지 마.
```

같은 스레드에서 A의 CX 확인 요청, 실제 CX 계정의 확인 결과, A의 최종 정리를 확인합니다. 다음으로 “2 더하기 3만 알려줘”처럼 일반 업무를 새 메시지에서 요청해 CX를 불필요하게 부르지 않는지 확인합니다. 후속 CS 질문은 같은 스레드에 멘션 없이 보내도 A가 처리하는지 확인합니다.

다음으로 정책 없이 최종 결정을 해야 하는 요청을 보냅니다. A가 근거를 만들어 확답하지 않고 `HUMAN_REVIEW_USER_ID`의 담당자를 같은 스레드에 실제 멘션하는지 확인합니다. 담당자는 main 허용 목록과 해당 채널에 포함되어야 합니다. 담당자 답변 후 A가 같은 스레드에서 이어가는지도 확인합니다. 실제 고객 발송과 환불은 하지 않습니다.

이 검사는 연결과 분기 기능을 확인합니다. 고객사 정책의 정답 검증은 실제 프롬프트와 예시를 받은 뒤 별도로 합니다.

## 구현 경계

전용 도구는 현재 허용된 Slack 채널과 요청 스레드만 사용하며 대상 CX는 설정된 한 명입니다. 다른 채널과 DM으로 위임하지 않습니다. A의 DM 자체는 일반 답변이 가능하지만, CX 호출 도구는 이 채널에서만 허용하므로 CX가 필요한 업무는 지정 채널에서 요청합니다.

한 번의 A 처리에서 CX 확인은 한 번입니다. 같은 도구 요청이 반복되면 프로세스 내부의 기존 결과를 사용합니다. 요청 상태가 불명확하거나 120초 안에 완성된 답이 오지 않으면 자동 재전송하지 않습니다. 4초 간격으로 요청 이후의 스레드 답글을 최대 100개씩 읽습니다. 페이지가 넘치면 다른 답을 추정해 사용하지 않고 오류로 종료합니다. 완성 표시와 확인번호, 실제 CX 계정과 bot ID가 모두 맞아야 결과로 인정합니다.

중복 방지 기록은 현재 프로세스 메모리에 10분간, 최대 128건 보관합니다. 서비스 재시작까지 견디는 영구적인 정확히 한 번 실행 보장은 아닙니다. 이 도구는 고객 발송이나 결제를 실행하지 않습니다. 장시간 업무와 대규모 병렬 요청은 현재 파일럿 범위가 아닙니다.

같은 계정을 쓰면 두 봇의 호출이 같은 계정의 사용량에 영향을 줄 수 있습니다. 정확한 한도와 차감은 해당 플랜에서 확인합니다. A가 CX를 부르면 각각 모델 호출을 하므로 단일 에이전트 처리보다 호출량이 늘 수 있습니다. API fallback은 없습니다. 구독 오류가 나면 처리에 실패할 수 있으며, 모델 호출 자체가 실패한 경우 사람 태그까지 보장되지는 않습니다.

다음으로 [설치 후 사용 가이드](../USAGE.md)와 [시행착오 기록](09-troubleshooting.md)을 운영자에게 전달합니다.

정책 부족, 정보 충돌, 승인 필요, 범위 밖 작업은 A가 사람 조율 도구를 선택합니다. CX 통신 오류와 시간 초과는 브리지에서 자동으로 사람 조율을 시도합니다. 담당자 한 명과 현재 허용된 스레드만 사용할 수 있고, 같은 처리 안에서는 한 번만 알립니다. Slack 장애 시에는 알림 자체도 실패할 수 있습니다. [상황별 사용 사례](11-use-cases.md)를 함께 전달합니다.

CX에게 직접 받은 요청의 조율 보고는 [CX 시작 경로](12-cx-first-coordination.md)를 따릅니다. A가 보낸 CX 확인을 A에게 다시 넘기거나 CX 보고를 CX에게 되돌리는 것은 도구가 거부합니다.
