# Hermes A와 CX, Slack 직원 구축 키트

다른 컴퓨터에서 환경을 확인하고 설치하는 데 필요한 문서, 설정 양식과 연결 플러그인입니다. **기존 사용자의 계정, 워크스페이스, 채널과 설치 상태는 가져오지 않습니다.**

처음에는 [SETUP.md](SETUP.md)를 읽습니다. 대상 환경을 질문하고 Codex, Tailscale, Aside와 Hermes 설치를 확인한 뒤 Slack 대상과 계정을 질문합니다. 필요한 답변을 받기 전에 ID를 채우거나 메시지를 보내지 않습니다.

## 읽는 순서

| 자료 | 목적 |
|---|---|
| [처음 설치 체크리스트](SETUP.md) | 준비되지 않은 Mac에서 도구 설치, 로그인과 대상 확인 |
| [에이전트 지침](AGENTS.md) | 인수받은 에이전트가 지킬 순서와 경계 |
| [프로필과 Slack 구축](docs/08-reproduce-a-cx.md) | main과 cx, OAuth, 앱과 서비스 구성 |
| [사용법](USAGE.md) | 설치 이후 팀원의 요청과 후속 답변 |
| [운영법](OPERATIONS.md) | 상태 확인, 재시작과 팀원 관리 |
| [CX 시작 조율](docs/12-cx-first-coordination.md) | CX가 먼저 A에게 보고하는 경로 |
| [요구사항 변경](docs/13-changing-requirements.md) | 역할과 정책, 연결 경계 수정 |
| [시행착오](docs/09-troubleshooting.md) | 다른 환경에서도 참고할 기술적 문제와 해결 |
| [검증 기준과 참고 결과](docs/10-live-verification.md) | 이전 개발 시험과 새 환경에서 다시 할 검사 구분 |

## 구현한 구조

사람이 A에게 요청하면 필요에 따라 실제 CX에게 확인합니다. 사람이 CX에게 직접 요청한 업무에서도 조율이 필요하면 CX가 A에게 보고할 수 있습니다. A는 결과를 정리하거나 같은 스레드에서 지정 담당자를 태그합니다.

현재 구현은 main과 cx 두 프로필, Slack 앱 두 개입니다. 각 프로필에서 ChatGPT 구독 OAuth를 승인합니다. 대상 계정과 플랜, 모델 접근은 설치 시 확인합니다. API fallback은 사용하지 않습니다. 고객 발송, 환불 실행, 데이터 수정과 파일 삭제 도구는 없습니다.

역할과 기준은 SOUL, 업무 절차는 제공받은 근거에 따른 스킬, 통신과 강제 제한은 플러그인으로 나눕니다. 실제 업무 프롬프트와 사례가 없으면 수집 양식만 만들고 정책을 지어내지 않습니다.

## 옮기는 것

이 폴더의 일반 문서, templates, manifests, plugins, scripts와 checks만 옮깁니다. `.env.example`은 비어 있는 입력 양식입니다. 인증값, state.json과 Slack 상태 JSON, 로그와 세션 DB, 브라우저 상태, private 폴더는 포함하지 않습니다. 기존 Slack ID와 개인 로컬 경로도 설치 기본값으로 넣지 않습니다.

GitHub에는 문서와 소스만 올립니다. ZIP과 캐시, 환경 상태는 `.gitignore`로 제외합니다. 새 컴퓨터에서는 저장소를 내려받고 인증과 환경 정보를 다시 준비합니다.

## 검사

Hermes 설치 후 확인한 전용 Python으로 실행합니다. 아래 경로는 source 설치의 예시이며 실제 경로가 다르면 바꿉니다.

```sh
~/.hermes/hermes-agent/venv/bin/python checks/validate_templates.py
~/.hermes/hermes-agent/venv/bin/python -m unittest discover -s checks -p 'test_*.py'
```

설정과 코드 검사가 통과해도 새 장치의 Slack 연결과 24시간 운영 검증을 대신하지 않습니다.
