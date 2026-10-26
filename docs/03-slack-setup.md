# Slack 연결 준비

## 먼저 질문할 항목

워크스페이스와 테스트 채널의 이름 또는 링크를 받습니다. 채널을 새로 만들지, 기존 채널을 쓸지 확인합니다. 두 Slack 앱을 새로 만들지 기존 앱을 이전할지도 구분합니다. 요청을 허용할 운영자와 팀원, 사람 조율 담당자와 시험 메시지 범위를 확인합니다.

접근 가능한 Slack 화면과 API에서 실제 ID를 확인합니다. 이름만으로 ID를 추측하거나 문서 속 과거 ID를 사용하지 않습니다. 확인한 값은 새 컴퓨터의 private 설치 기록에만 두며 재배포에는 포함하지 않습니다.

## 앱별 필수 확인

- main과 cx에 서로 다른 Slack 앱을 연결합니다.
- 매니페스트는 manifests의 해당 pilot.json을 사용합니다.
- Socket Mode와 connections:write app token, 설치된 bot token을 준비합니다.
- channels:history, groups:history, files:read 권한을 확인합니다.
- app_mention, message.channels, message.groups, message.im 이벤트를 확인합니다.
- App Home의 Messages Tab과 메시지 입력을 켭니다.
- 지정 테스트 채널에 두 봇을 모두 초대합니다.
- 토큰은 실제 프로필 .env에만 입력하고 600 권한을 유지합니다.

현재 설정에서는 A가 일반 스레드 후속 답변을 받고 CX는 매번 명시적인 멘션을 요구합니다. 두 봇은 허용된 상대 봇이 자신을 멘션한 경우만 봇 이벤트를 받습니다. 다른 봇 전체를 수신하지 않습니다.

실제 ID 적용과 서비스 설치는 [최신 구축 가이드](08-reproduce-a-cx.md)를 따릅니다. 비밀번호 재확인과 Slack 설치 승인은 사용자가 직접 합니다.
