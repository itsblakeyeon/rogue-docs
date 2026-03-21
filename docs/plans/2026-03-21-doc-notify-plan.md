# 문서 변경 Slack 알림 — 구현 계획

**Goal:** `main` push 시 프로젝트 문서 변경을 `#1-do` 프로젝트별 스레드로 알림

**Architecture:** GitHub Actions 워크플로우가 push 이벤트를 받아, Node.js 스크립트로 변경 감지 → Slack API 호출 → 스레드 매핑 JSON 업데이트

**Tech Stack:** GitHub Actions, Node.js (스크립트), Slack Web API (fetch), Git

---

### Task 1: 스레드 매핑 JSON 생성

**Files:**
- Create: `.github/slack-threads.json`

**Step 1: 빈 매핑 파일 생성**

```json
{}
```

프로젝트명(예: "병원마케팅")을 키로, Slack 스레드 ts를 값으로 저장할 파일.

---

### Task 2: 알림 스크립트 작성

**Files:**
- Create: `.github/scripts/doc-notify.mjs`

**Step 1: 스크립트 작성**

기능:
1. 환경변수에서 변경 파일 목록, 커밋 메시지, SLACK_BOT_TOKEN 읽기
2. `4-프로젝트/{이름}/` 패턴의 `.md` 파일만 필터링
3. 프로젝트별로 그룹핑
4. `.github/slack-threads.json` 읽기
5. 각 프로젝트에 대해:
   - 스레드 ts 있으면 → `chat.postMessage`로 reply
   - 없으면 → `chat.postMessage`로 새 메시지 → 반환된 ts 저장
6. 매핑 변경 시 JSON 파일 갱신

입력(환경변수):
- `CHANGED_FILES` — 줄바꿈 구분 파일 목록
- `COMMIT_MESSAGE` — 커밋 메시지
- `SLACK_BOT_TOKEN` — Slack Bot 토큰
- `SLACK_CHANNEL_ID` — `#1-do` 채널 ID (C0AM5077A0Z)

---

### Task 3: GitHub Actions 워크플로우 작성

**Files:**
- Create: `.github/workflows/doc-notify.yml`

**Step 1: 워크플로우 작성**

```yaml
name: 문서 변경 알림
on:
  push:
    branches: [main]
    paths:
      - '4-프로젝트/**/*.md'
```

Steps:
1. Checkout (fetch-depth: 2, 직전 커밋과 비교용)
2. `git diff --name-only HEAD~1 HEAD`로 변경 파일 추출
3. Node.js 설정
4. `doc-notify.mjs` 실행 (환경변수로 변경 파일, 커밋 메시지, 토큰 전달)
5. `slack-threads.json` 변경 시 자동 커밋+push

시크릿:
- `SLACK_BOT_TOKEN` — GitHub repo settings에서 설정

---

### Task 4: 테스트

**Step 1: 로컬 테스트**

`.md` 파일을 하나 변경하고 push해서 알림이 `#1-do`에 도착하는지 확인.

**Step 2: 스레드 reply 테스트**

같은 프로젝트의 `.md` 파일을 다시 변경하고 push. 같은 스레드에 reply가 달리는지 확인.
