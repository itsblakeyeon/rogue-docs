# Handoff

## 목표
병원 이메일 크롤링 + 검증 완료 → 영업 이메일 리스트 확보.

## 완료

### 크롤링 파이프라인 (2026-03-20)
- **HIRA 파이프라인** — 서울+경기 피부과/성형외과 6,971건 전수 수집
- **네이버 구 단위 검색** — 56지역 × 피부과/성형외과 (페이지네이션 5페이지, 25건/쿼리)
- **네이버 동 단위 세부 검색** — 서울 25개구 주요동 + 경기 6개시 구단위
- **네이버 키워드 변형** — 피부클리닉/스킨클리닉/피부미용/성형클리닉 추가 검색
- **HIRA 병원명 개별 네이버 검색** — 웹사이트 없는 5,527건 → 4,577건 URL 보강 (느슨한 매칭)
- **이메일 크롤링 (deep)** — 홈페이지 + contact 페이지 + 하위 경로 자동 탐색
- **전체 합산 + 포털 이메일 필터링**

### 이메일 검증 (2026-03-20)
- **쓰레기 이메일 제거** — YouTube 지원 이메일(194건), 플레이스홀더, CSS/JS 파싱 오류
- **대행사/웹에이전시 필터링** — beautyleader, boazent, cunetwork, maylin, web2002 등 27개 도메인
- **MX 레코드 검증** — 도메인 이메일 수신 가능 여부 DNS 확인
- **형식 검증** — regex + 비정상 패턴 제거

### 최종 결과

| 항목 | 수치 |
|------|------|
| 전체 병원 (중복 제거) | 6,901건 |
| URL 보유 | 6,021건 (87%) |
| 이메일 확보 (검증 전) | 1,123건 |
| **이메일 확보 (검증 후)** | **883건** |
| 제거: 쓰레기 | 194건 |
| 제거: 대행사/에이전시 | 52건 |
| 제거: MX 레코드 없음 | 11건 |
| 제거: 형식/패턴 오류 | 50건 |

### 이전 세션 (제안서)
- 제안서 PDF 생성 완료 (`병원 매출 성장 제안서 - ROGUE.pdf`)
- 이메일 `blake@therogues.xyz`로 변경
- FeatPaper 트래킹 링크: `https://featpaper.com/v/O5cZTBCt`

## 미완료
- **이메일 발송 캠페인** — Stibee로 콜드 이메일 세팅 (500명 무료 티어)
- **HIRA specialty 매핑** — HIRA 출처 877건은 specialty 미분류. 피부과/성형외과만 필터링 필요

## 결정 사항
- 피부과/성형외과에 집중 (priority 1)
- HIRA = 전수조사 기준, 네이버 = URL/이메일 보강 + 신규 병원 발견
- 네이버 API 키 순서: `NAVER_CLIENT_ID=TBhAzdUpqs_8BCJFy7d_` (ID와 Secret이 직관적 순서와 반대)
- 대행사/웹에이전시 이메일은 병원 자체 이메일이 아니므로 제거
- 포털 이메일(naver, gmail 등)은 유지 (개인 병원에서 많이 사용)

## 주의 사항
- 네이버 API 일일 25,000건 제한
- HIRA API 일일 1,000건 제한
- `crawling/output/` 디렉토리의 CSV는 `.gitignore`에 포함
- 검증 스크립트에 대행사 도메인 블랙리스트 있음 (`validate_emails.py`의 `AGENCY_DOMAINS`)

## 결과 파일 위치
- `crawling/output/all_hospitals_valid_email.csv` — **최종 유효 이메일 리스트 (883건)**
- `crawling/output/rejected_emails.csv` — 제거된 이메일 상세 (사유 포함)
- `crawling/output/all_hospitals_with_email.csv` — 검증 전 이메일 (1,123건)
- `crawling/output/all_hospitals_merged.csv` — 전체 병원 합산 (6,901건)
- `crawling/output/step3_hospitals_enriched_final.csv` — HIRA + 네이버 URL 보강 + 이메일
- `crawling/output/hira_naver_enriched.csv` — HIRA 병원명 네이버 검색 결과

## 변경된 파일 (이번 세션)
- `crawling/src/naver_client.py` — 페이지네이션 추가 (max_pages)
- `crawling/src/email_crawler.py` — deep crawl (SUBPAGE_PATHS, contact 키워드 확대)
- `crawling/src/naver_enrich_hira.py` — **신규** (HIRA 병원명 네이버 검색 + 느슨한 매칭)
- `crawling/src/apply_naver_enrichment.py` — **신규** (네이버 URL을 HIRA에 반영)
- `crawling/src/validate_emails.py` — **신규** (이메일 검증: 쓰레기/대행사/MX/형식)
- `crawling/src/merge_and_cleanup.py` — enriched HIRA 파일 우선 사용하도록 수정
- `crawling/.env` — 네이버 API 키 추가

## 영업 진행 상황
- 레픽의원 하용훈 원장 미팅 — 2026-03-24(월) 오전 9:30
- 월매출 8억 피부과 1곳 미팅 확보
- 제너러티브랩 통해 병원 소개 받는 중
- VC 형 통해 개원의 소개 연결 중

## 다음 단계
1. **Stibee 콜드 이메일 캠페인 세팅** — 제안서 PDF + FeatPaper 링크 포함
2. **레픽의원 미팅 준비** (3/24 월)
3. 필요 시 다른 진료과목(치과, 안과 등) 크롤링 확장
