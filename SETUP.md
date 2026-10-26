# 새 컴퓨터에서 처음 시작하기

이 문서는 설치 전 안내입니다. 기존 운영자의 계정, 채널, 로그인 상태와 설치 경로를 기본값으로 사용하지 않습니다. 환경 상태와 인증 파일은 이 자료에 포함하지 않습니다.

## 1. 설치 전에 확인할 것

설치 담당 에이전트는 새 대상 컴퓨터인지 확인하고 다음 질문을 먼저 합니다. 현재 대화에서 이미 확인한 내용은 다시 묻지 않습니다. 읽기 전용 환경 확인은 답변을 기다리는 동안 진행할 수 있습니다.

- 이 컴퓨터가 실제 상주 서버인가요, 준비용 컴퓨터인가요? OS와 CPU는 무엇인가요?
- Codex는 데스크톱에서 사용할까요, 터미널에서 사용할까요? 사용할 ChatGPT 계정과 플랜은 무엇인가요?
- Tailscale은 어느 계정과 tailnet에 연결하나요? 원격으로 접속할 상대 장치는 무엇인가요?
- Aside에서 Slack에 로그인할 브라우저 계정은 무엇인가요? 기존 로그인 상태를 사용할까요?

비밀번호, 로그인 코드, 토큰과 키 자체는 답변으로 받지 않습니다. 계정 선택과 승인 화면은 사용자가 직접 처리합니다. Tailscale의 장치 등록은 대상 tailnet을 확인한 뒤 진행합니다.

## 2. 설치 체크리스트

앱이 있다는 사실과 로그인 및 연결 성공을 구분해 기록합니다. 설치되어 있으면 중복 설치나 일괄 업데이트를 하지 않습니다.

| 항목 | 확인 | 없을 때 할 일 | 완료 기준 |
|---|---|---|---|
| Codex | 앱 실행 또는 `command -v codex`, `codex --version` | 아래 공식 방법으로 선택한 형태 설치 | ChatGPT 로그인, 이 자료 폴더 접근 가능 |
| Tailscale | 앱 설치와 실행, 대상 tailnet 연결 확인 | 공식 macOS 설치 안내 사용 | 사용자가 지정한 tailnet에서 대상 장치 확인 |
| Aside | `command -v aside`, `aside --version` | 아래 installer 실행 | `aside guide` 읽기, 선택한 브라우저로 Slack 접근 확인 |
| Hermes | `command -v hermes`, `hermes --version` | 아래 공식 CLI installer 사용 | 전용 Python, doctor 결과와 Slack 의존성 확인 |

Codex가 아직 없다면 사람이 먼저 Codex를 설치하고 이 폴더를 열어야 에이전트에게 나머지 구축을 맡길 수 있습니다. 나머지 설치를 이미 다른 에이전트가 수행 중이라면 해당 도구 설치를 이어갑니다.

### Codex

데스크톱은 [OpenAI 공식 앱 안내](https://learn.chatgpt.com/docs/app)에서 현재 OS용 앱을 설치하고 ChatGPT 계정으로 로그인합니다. 제품명과 배포 방식은 설치 시점의 공식 안내를 따릅니다. 데스크톱에서 이 자료 폴더를 선택해 Codex 작업을 시작합니다.

터미널은 [공식 Codex CLI 안내](https://learn.chatgpt.com/docs/cli)를 확인합니다. 2026-10-26 확인한 macOS와 Linux 설치 명령은 다음과 같습니다.

```sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
codex
```

처음 실행 시 ChatGPT 로그인 방식을 선택합니다. API 키 로그인과 API fallback은 이번 구성에서 사용하지 않습니다. Codex 작업 도구의 로그인과 Hermes 두 프로필의 OAuth 승인은 별도 단계입니다.

### Tailscale

[공식 macOS 설치 안내](https://tailscale.com/docs/install/mac)에서 배포본을 선택합니다. 기존 설치가 있으면 같은 배포 방식을 유지하고 중복 설치하지 않습니다. 설치 후 앱을 열고 macOS의 VPN 구성 승인을 사용자에게 안내한 뒤 확인한 계정으로 로그인합니다.

어느 tailnet인지 확인하기 전에 임의 계정으로 연결하지 않습니다. 연결 뒤 대상 장치가 보이는지 확인하고 필요한 원격 접근을 별도 시험합니다. Tailscale 설치만으로 SSH와 화면 공유 권한까지 설정된 것으로 보지 않습니다. 공개 Funnel, 서브넷 라우팅과 exit node는 요청이 없으면 설정하지 않습니다.

### Aside

먼저 [Aside 공식 다운로드](https://aside.com/download)에서 대상 컴퓨터용 브라우저 앱을 설치하고 실행합니다. macOS에서는 DMG의 Aside를 Applications로 옮긴 뒤 열고 사용자 계정으로 초기 설정합니다.

에이전트가 브라우저를 조작할 CLI도 별도로 확인합니다. 다음 installer는 Aside CLI용입니다. 설치 전에 현재 배포 안내와 스크립트를 확인하고 실행합니다.

```sh
curl -fsSL https://releases.aside.com/install.sh | bash
aside --version
aside guide
```

설치가 실패하면 오류를 기록하고 중단한 부분부터 해결합니다. CLI가 있어도 로그인된 브라우저가 자동으로 준비된 것은 아닙니다. `aside guide`의 현재 안내를 읽고 사용자가 지정한 브라우저 계정에서 Slack 로그인을 준비합니다. `aside repl`을 사용하려면 먼저 `aside guide repl`을 읽습니다. 기존 브라우저 쿠키와 Aside 세션 폴더를 이 자료에 복사하지 않습니다.

### Hermes

[공식 설치 문서](https://hermes-agent.nousresearch.com/docs/getting-started/installation)에 따라 CLI 설치를 진행합니다.

```sh
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes --version
hermes doctor
```

기존 default 프로필과 다른 서비스를 보존합니다. 공식 설치가 사용하는 전용 Python을 확인하고 시스템 Python을 덮어쓰지 않습니다. Slack 모듈이 없으면 해당 Hermes 버전의 의존성을 확인해 추가합니다. 검증에 사용한 버전과 새 설치 버전은 다를 수 있으므로 기존 명령과 플러그인의 호환성을 검사합니다.

## 3. 설치 뒤 Slack 대상 질문

프로필에 ID를 채우거나 앱을 생성하기 전에 아래를 질문합니다. 워크스페이스와 테스트 채널이 확인되기 전에는 메시지를 보내지 않습니다.

| 확인할 항목 | 답변 |
|---|---|
| Slack 워크스페이스 이름 또는 URL | 미확인 |
| 테스트 채널 이름 또는 링크 | 미확인 |
| 기존 채널 사용 또는 새 채널 생성 | 미확인 |
| 새 Slack 앱 두 개 생성 또는 기존 앱 이전 | 미확인 |
| 요청을 허용할 운영자와 팀원 | 미확인 |
| 사람 조율 담당자 | 미확인, 운영자와 같은지 질문 |
| 스레드 시험 메시지 전송 범위 | 미확인 |
| 실제 업무 프롬프트와 대표 입출력 예시 유무 | 미확인 |

사람이 이름이나 채널 링크로 답하면 접근 가능한 Slack 화면과 API로 실제 ID를 확인합니다. 이름만 보고 ID를 추측하지 않습니다. 기본 main과 cx 이름이 이미 사용 중인지도 확인합니다.

답변과 비밀이 아닌 설치 기록은 새 컴퓨터의 `private/setup-context.md`에만 기록할 수 있습니다. 토큰, 키, 비밀번호와 인증 코드는 이 파일에도 기록하지 않습니다. private 폴더는 재배포 압축본에서 제외합니다.

## 4. 프로필 구축

선행 도구와 대상 확인이 끝나면 [실제 구축 가이드](docs/08-reproduce-a-cx.md)를 진행합니다. 템플릿의 허용 사용자와 관리자 목록은 비어 있으므로 그대로 서비스를 시작하지 않습니다. 확인한 ID를 apply_profiles에 전달해 채운 뒤 실행합니다.

새 앱을 만들면 새 ID를 사용합니다. 기존 앱을 다른 컴퓨터로 이전할 때만 전환 직전에 기존 장치의 두 서비스를 중지합니다. 별도의 새 앱으로 시험하는 상황에서 기존 운영 서비스를 중지하지 않습니다.

## 완료 기록

- [ ] 대상 OS와 CPU, 설치할 컴퓨터 역할 확인
- [ ] Codex 설치와 사용자 로그인, 자료 폴더 열기
- [ ] Tailscale 설치와 올바른 tailnet 연결
- [ ] Aside 설치, guide 확인, 사용할 Slack 브라우저 로그인
- [ ] Hermes 설치, 전용 Python과 doctor 확인
- [ ] 워크스페이스, 테스트 채널과 앱 생성 또는 이전 방식 확인
- [ ] 운영자, 허용 사용자와 사람 조율 담당자 확인
- [ ] 프로필별 OAuth 승인과 Slack 토큰 준비
- [ ] 실제 ID 적용, 설정 검사, 플러그인 테스트
- [ ] A 시작, CX 시작, 사람 태그를 지정 테스트 스레드에서 확인
- [ ] 재시작, 절전과 재부팅 후 복구 확인
- [ ] 실제 완료와 미확인 항목을 구분해 보고
