# 서울경기권 병원 이메일 크롤링 구현 계획

**Goal:** 서울·경기 의원/병원급 의료기관의 이메일 및 메타데이터를 HIRA API + 웹 크롤링으로 수집하여 CSV 출력

**Architecture:** 3단계 파이프라인 — (1) HIRA API로 병원 목록+메타데이터 수집 → (2) 누락 URL을 네이버 검색으로 보강 → (3) 각 병원 웹사이트에서 이메일 추출. 중간 결과는 CSV로 저장하여 단계별 재실행 가능.

**Tech Stack:** Python 3.11+, requests, BeautifulSoup4, playwright, pandas, python-dotenv

---

## Task 1: 프로젝트 구조 및 의존성 설정

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tests/__init__.py`

**Step 1: requirements.txt 작성**

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
pandas>=2.1.0
python-dotenv>=1.0.0
playwright>=1.40.0
```

**Step 2: .gitignore 작성**

```
__pycache__/
*.pyc
.env
output/
*.log
.venv/
```

**Step 3: .env.example 작성**

```
HIRA_API_KEY=your_api_key_from_data_go_kr
```

**Step 4: src/config.py 작성**

설정 상수 정의:
- HIRA API base URL, 엔드포인트
- 서울/경기 시도코드 (110000, 410000)
- 의원/병원 종별코드
- 요청 딜레이, 타임아웃
- 출력 디렉토리 경로

**Step 5: 가상환경 생성 및 의존성 설치**

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium
```

**Step 6: 커밋**

```bash
git init && git add -A && git commit -m "chore: initial project setup with dependencies"
```

---

## Task 2: HIRA API 클라이언트 — 병원 기본 목록 수집 (depends on: Task 1)

**Files:**
- Create: `src/hira_client.py`
- Create: `tests/test_hira_client.py`

**Step 1: 테스트 작성 — API 응답 파싱**

`tests/test_hira_client.py`:
- `test_parse_hospital_item`: XML 응답 아이템을 파싱하여 dict로 변환하는 로직 테스트
- `test_filter_by_institution_type`: clCd 필터링 (의원=31, 병원=11 등) 테스트
- `test_pagination_params`: 페이지네이션 파라미터 생성 테스트

**Step 2: 테스트 실행 — 실패 확인**

```bash
python -m pytest tests/test_hira_client.py -v
```

Expected: FAIL — import 에러

**Step 3: src/hira_client.py 구현**

- `HiraClient` 클래스
  - `__init__(api_key)`: API 키 설정
  - `fetch_hospitals(sido_cd, clCd, page, num_of_rows)`: 기본 목록 API 호출
  - `parse_response(xml_text)`: XML → list[dict] 파싱
  - `fetch_all_hospitals(sido_cd, clCd)`: 전체 페이지 순회, 딜레이 적용
- 추출 필드: yadmNm, addr, telno, hospUrl, clCdNm, sidoCdNm, sgguCdNm, emdongNm, estbDd, ykiho, drTotCnt

**Step 4: 테스트 실행 — 통과 확인**

```bash
python -m pytest tests/test_hira_client.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/hira_client.py tests/test_hira_client.py && git commit -m "feat: HIRA API client for hospital basic list"
```

---

## Task 3: HIRA 상세정보 API — 진료과목, 병상수 (depends on: Task 2)

**Files:**
- Modify: `src/hira_client.py`
- Modify: `tests/test_hira_client.py`

**Step 1: 테스트 추가**

- `test_parse_department_info`: 진료과목 XML 파싱 테스트
- `test_parse_bed_info`: 병상수 XML 파싱 테스트
- `test_aggregate_departments`: 복수 진료과목을 쉼표 구분 문자열로 변환

**Step 2: 테스트 실행 — 실패 확인**

**Step 3: HiraClient에 메서드 추가**

- `fetch_departments(ykiho)`: getDgsbjtInfo2.7 호출 → 진료과목 코드/이름 리스트
- `fetch_bed_count(ykiho)`: getEqpInfo2.7 호출 → 총 병상수 합산
- `enrich_hospital_details(hospitals)`: 각 병원에 진료과목, 병상수 추가. 요청 간 딜레이.

**Step 4: 테스트 실행 — 통과 확인**

**Step 5: 커밋**

```bash
git add src/hira_client.py tests/test_hira_client.py && git commit -m "feat: HIRA detail API for departments and bed counts"
```

---

## Task 4: 1단계 파이프라인 스크립트 — 병원 목록 수집 실행 (depends on: Task 3)

**Files:**
- Create: `src/step1_collect.py`

**Step 1: 스크립트 작성**

- `.env`에서 API 키 로드
- 서울(110000) + 경기(410000) 순회
- 의원(clCd=31) + 병원(clCd=11) 수집
- 각 병원의 상세정보(진료과목, 병상수) 추가 조회
- 중간 결과를 `output/step1_hospitals_raw.csv`로 저장
- 진행률 로깅 (N/total 병원 처리됨)
- 이미 수집된 ykiho는 스킵 (재실행 지원)

**Step 2: 테스트 실행 (소규모)**

```bash
python src/step1_collect.py --test --limit 10
```

Expected: `output/step1_hospitals_raw.csv`에 10건 저장

**Step 3: 커밋**

```bash
git add src/step1_collect.py && git commit -m "feat: step1 pipeline script for HIRA hospital collection"
```

---

## Task 5: URL 보강 모듈 (depends on: Task 4)

**Files:**
- Create: `src/url_enricher.py`
- Create: `tests/test_url_enricher.py`

**Step 1: 테스트 작성**

- `test_extract_url_from_search_result`: 네이버 검색 결과 HTML에서 병원 URL 추출
- `test_validate_url`: URL 유효성 검증 (응답 200, 타임아웃 처리)
- `test_skip_portal_urls`: 네이버/카카오 등 포털 URL은 제외

**Step 2: 테스트 실행 — 실패 확인**

**Step 3: 구현**

- `UrlEnricher` 클래스
  - `search_hospital_url(hospital_name, address)`: 네이버 검색으로 병원 공식 URL 찾기
  - `validate_url(url)`: HTTP HEAD 요청으로 유효성 확인
  - `enrich_urls(hospitals_df)`: hospUrl 없는 병원에 URL 추가
- User-Agent 설정, 요청 딜레이

**Step 4: 테스트 실행 — 통과 확인**

**Step 5: 커밋**

```bash
git add src/url_enricher.py tests/test_url_enricher.py && git commit -m "feat: URL enrichment via search for hospitals without websites"
```

---

## Task 6: 2단계 파이프라인 스크립트 — URL 보강 (depends on: Task 5)

**Files:**
- Create: `src/step2_enrich_urls.py`

**Step 1: 스크립트 작성**

- `output/step1_hospitals_raw.csv` 읽기
- hospUrl이 비어있는 행에 대해 URL 검색 수행
- 결과를 `output/step2_hospitals_with_urls.csv`로 저장
- 진행률 로깅

**Step 2: 테스트 실행 (소규모)**

```bash
python src/step2_enrich_urls.py --limit 10
```

**Step 3: 커밋**

```bash
git add src/step2_enrich_urls.py && git commit -m "feat: step2 pipeline script for URL enrichment"
```

---

## Task 7: 이메일 크롤러 모듈 (depends on: Task 1)

**Files:**
- Create: `src/email_crawler.py`
- Create: `tests/test_email_crawler.py`

**Step 1: 테스트 작성**

- `test_extract_emails_from_html`: HTML에서 이메일 정규식 + mailto: 추출
- `test_deduplicate_emails`: 중복 이메일 제거
- `test_filter_invalid_emails`: 이미지 파일명 등 잘못된 매칭 제외 (e.g., banner@2x.png)
- `test_find_contact_page_links`: "연락처", "문의", "contact" 등 링크 찾기
- `test_extract_representative_name`: 페이지에서 "대표원장", "원장" 등 이름 추출 시도

**Step 2: 테스트 실행 — 실패 확인**

**Step 3: 구현**

- `EmailCrawler` 클래스
  - `__init__(use_playwright=False)`: requests 기본, 필요시 playwright
  - `fetch_page(url)`: HTML 가져오기 (requests → 실패시 playwright fallback)
  - `extract_emails(html)`: 정규식 + mailto: 파싱, 필터링, 중복제거
  - `find_contact_pages(html, base_url)`: 연락처 관련 서브페이지 링크 추출
  - `extract_representative_name(html)`: 대표원장명 추출 시도
  - `crawl_hospital(url)`: 메인 페이지 → 연락처 페이지 순서로 이메일 탐색
- 이메일 정규식: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
- 제외 패턴: 이미지 확장자, noreply, webmaster 등

**Step 4: 테스트 실행 — 통과 확인**

**Step 5: 커밋**

```bash
git add src/email_crawler.py tests/test_email_crawler.py && git commit -m "feat: email crawler with contact page detection and name extraction"
```

---

## Task 8: 3단계 파이프라인 스크립트 — 이메일 크롤링 (depends on: Task 6, Task 7)

**Files:**
- Create: `src/step3_crawl_emails.py`

**Step 1: 스크립트 작성**

- `output/step2_hospitals_with_urls.csv` 읽기
- hospUrl이 있는 각 병원에 대해 이메일 크롤링
- 대표원장명도 웹사이트에서 추출 시도
- 결과를 `output/step3_hospitals_final.csv`로 저장
- 이메일 있는 것만 필터 → `output/hospitals_with_email.csv`
- 진행률 로깅, 실패 URL 기록
- 재실행 시 이미 크롤링된 URL 스킵

**Step 2: 테스트 실행 (소규모)**

```bash
python src/step3_crawl_emails.py --limit 10
```

**Step 3: 커밋**

```bash
git add src/step3_crawl_emails.py && git commit -m "feat: step3 pipeline script for email crawling"
```

---

## Task 9: 메인 실행 스크립트 및 마무리 (depends on: Task 4, Task 6, Task 8)

**Files:**
- Create: `src/main.py`
- Create: `README.md` (간단한 사용법)

**Step 1: main.py 작성**

- 전체 파이프라인 순차 실행 (step1 → step2 → step3)
- `--step` 옵션으로 특정 단계만 실행 가능
- `--limit` 옵션으로 테스트용 소규모 실행
- 최종 통계 출력 (총 병원 수, URL 보유율, 이메일 수집률)

**Step 2: 전체 파이프라인 테스트 (소규모)**

```bash
python src/main.py --limit 5
```

Expected: output/ 디렉토리에 모든 CSV 파일 생성

**Step 3: 커밋**

```bash
git add src/main.py README.md && git commit -m "feat: main pipeline orchestrator with step/limit options"
```

---

## 최종 CSV 컬럼 정의

| 컬럼명 | 설명 | 소스 |
|--------|------|------|
| hospital_name | 병원명 | HIRA |
| institution_type | 종별 (의원/병원) | HIRA |
| specialty | 세부업종 (주진료과목) | HIRA |
| departments | 전체 진료과목 (쉼표 구분) | HIRA detail |
| address | 전체 주소 | HIRA |
| sido | 시도 | HIRA |
| sigungu | 시군구 | HIRA |
| dong | 읍면동 | HIRA |
| phone | 전화번호 | HIRA |
| website | 홈페이지 URL | HIRA + 검색 보강 |
| email | 이메일 | 웹 크롤링 |
| representative | 대표원장명 | 웹 크롤링 |
| bed_count | 병상수 | HIRA detail |
| doctor_count | 의사수 | HIRA |
| established_date | 개원일 | HIRA |
| ykiho | 기관 고유 ID | HIRA |

---

## 의존성 그래프

```
Task 1 (프로젝트 설정)
  ├── Task 2 (HIRA 기본 목록)
  │     └── Task 3 (HIRA 상세정보)
  │           └── Task 4 (1단계 스크립트)
  │                 └── Task 5 (URL 보강 모듈)
  │                       └── Task 6 (2단계 스크립트)
  │                             └── Task 8 (3단계 스크립트)
  │
  └── Task 7 (이메일 크롤러 모듈) ──────┘

Task 8 → Task 9 (메인 스크립트)
```

Note: Task 7은 Task 1에만 의존하므로 Task 2~6과 병렬 구현 가능.
