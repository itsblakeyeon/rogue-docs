# Handoff

## 목표
콜드 이메일 캠페인 세팅 — 717건 병원 이메일 발송 + 오픈/클릭 트래킹 시스템 구축, 3/24(월) 09:00 KST 예약 발송.

## 완료

### 콜드 이메일 시스템 (2026-03-20)
- **데이터 정제**: 원본 883건 → 쉼표 이메일 분리 → 형식 검증 → 중복 제거 → **717건 유니크 이메일**
- **Google Sheets 트래커 생성**: 718건 (717 병원 + 본인 1건)
  - 스프레드시트 ID: `1A64Dd8ToVD1emey8r4e3w2Q9GvWiSza8gaupCHagH0A`
  - 시트1: 수신자 목록 (id, 이메일, 병원명, 지역, 진료과목, 발송여부, 오픈, 클릭 등)
  - 로그 시트: 트래킹 이벤트 로그 (타임스탬프, id, 이벤트, 이메일)
- **Apps Script 트래킹 웹앱**: 배포 완료 (v6)
  - Script ID: `1azrOwCtfTRE_-S7xRREnjV-9q3agDftTR4ZfvVs4va3u51csvAaG1Zh6`
  - 오픈 트래킹: 1x1 투명 픽셀 → 시트 기록
  - 클릭 트래킹: 리다이렉트 → featpaper.com 제안서로 이동 + 시트 기록
  - 발송 함수: `sendAllEmails()` — 시트 읽으면서 개인화 이메일 발송, 중복 방지
  - 예약 트리거: `setScheduledTrigger()` 실행 완료 → **3/24(월) 09:00 KST 자동 발송**
- **이메일 본문**: HTML, 콜드메일 톤
  - 발신자: 연준현 (blake@therogues.xyz)
  - 제목: `{병원명} 원장님, 마케팅 대행사가 매출까지 추적해주고 있나요?`
  - 본문 첫 줄: `안녕하세요, {병원명} 원장님.`
  - 제안서 링크: 클릭 트래킹 거쳐서 featpaper.com으로 리다이렉트
- **DNS 설정**: SPF 레코드 추가, DKIM 기존 확인, DMARC 추가 (가비아)
- **Vercel 리다이렉트**: `therogues.xyz/proposal` → featpaper 제안서. vercel.json 생성 + 배포 완료
- **blake@therogues.xyz Google Workspace MCP 인증 완료**

### 스티비 (중단)
- 주소록 "서울경기 병원 콜드 이메일" 생성 후 303건 업로드 → 전체 삭제
- 무료 플랜 500명 제한 + 푸터 문제로 Gmail 발송으로 전환

### 이전 세션 (크롤링)
- HIRA + 네이버 파이프라인으로 883건 유효 이메일 확보
- 제안서 PDF + FeatPaper 트래킹 링크 완료

## 미완료
- 없음. 3/24 09:00 자동 발송 트리거 설정까지 완료.

## 결정 사항
- **스티비 → Gmail 전환**: 무료 푸터 + 500명 제한. Gmail Apps Script로 푸터 없이 무제한 발송
- **트래킹 자체 구축**: Google Sheets + Apps Script 웹앱. 외부 서비스 없이 오픈/클릭 추적
- **병원명 개인화**: 제목 + 본문에 병원명 삽입. 타겟팅 메일 느낌
- **featpaper 직접 링크**: therogues.xyz/proposal이 아닌 featpaper.com으로 직접 리다이렉트 (Apps Script iframe 제약)
- **발송 시간**: 월요일 오전 9시 — 병원 원장 메일 확인 패턴 기반
- **10건마다 3초 딜레이**: 스팸 분류 방지

## 주의 사항
- Google Workspace 일일 발송 한도: 2,000건/일. 718건은 여유 있음
- `sendAllEmails()`는 발송여부 `O`인 행 스킵 → 중복 발송 방지
- 스티비 주소록은 비어있는 상태 (303건 전체 삭제 완료). 스티비 계정 자체는 살아있음
- `crawling/output/` CSV 파일들은 `.gitignore`에 포함
- Apps Script 배포 시 manifest(appsscript.json)와 Code.gs를 반드시 함께 업데이트해야 함 (따로 하면 코드 파일이 날아감)

## 결과 파일 위치
- `crawling/output/cold_email_tracker.csv` — 최종 발송 데이터 (717건, UUID 포함)
- `crawling/output/stibee_all_clean.csv` — 클린 데이터 (717건)
- `crawling/output/all_hospitals_valid_email.csv` — 원본 유효 이메일 (883건)
- `website/vercel.json` — /proposal 리다이렉트 설정
- `cold-email.md` — 콜드 이메일 초안 (원본)

## 관련 리소스
- Google Sheets: https://docs.google.com/spreadsheets/d/1A64Dd8ToVD1emey8r4e3w2Q9GvWiSza8gaupCHagH0A
- Apps Script: https://script.google.com/d/1azrOwCtfTRE_-S7xRREnjV-9q3agDftTR4ZfvVs4va3u51csvAaG1Zh6/edit
- 제안서: https://featpaper.com/v/O5cZTBCt
- 웹사이트: https://therogues.xyz

## 다음 단계
1. **3/24(월) 09:00 이후** — Google Sheets에서 발송 결과 확인 (발송여부, 오픈, 클릭)
2. **오픈/클릭 데이터 기반 팔로업** — 클릭한 병원 우선 연락
3. **레픽의원 미팅** (3/24 월 09:30)
4. **2차 배치 발송** (요금제 업그레이드 시) 또는 추가 크롤링 확장
