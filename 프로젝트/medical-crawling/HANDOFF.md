# Handoff

## 목표
서울경기권 의원/병원급 의료기관의 이메일을 크롤링하여 CSV로 수집. HIRA API + 네이버 지역검색 API 두 소스를 모두 활용하여, 9개 진료과목(피부과, 성형외과, 치과, 안과, 내과, 가정의학과, 정형외과, 재활의학과, 한의원) 전체를 커버.

## 완료
- HIRA 파이프라인 1~5순위 전체 완료 (Step 1 목록수집 → Step 2 URL보강 → Step 3 이메일크롤링)
- 치과/한방 별도 종별코드 수집 로직 구현 (`DEPT_TO_INSTITUTION_CODES` in `config.py`)
- 네이버 지역검색 API 연동 (`naver_client.py`, `naver_collect.py`)
- 네이버 세부 수집 — 서울 25구 동단위 + 경기 6개시 구단위 (`naver_collect_detail.py`)
- 네이버 이메일 크롤링 (`naver_crawl_emails.py`)
- HIRA + 네이버 데이터 합산 + 포털이메일 cleanup (`merge_and_cleanup.py`)
- CLAUDE.md 업데이트 (네이버 파이프라인 반영)
- GitHub push 완료 (https://github.com/itsblakeyeon/rogue-code)

### 최종 수치 (2026-03-19)
- 총 병원: 14,196건
- 유효 이메일: 1,175건 (HIRA 583 + 네이버 592)
- 진료과목별: 피부과 135, 치과 114, 성형외과 74, 안과 63, 가정의학과 59, 정형외과 56, 한의원 42, 재활의학과 26, 내과 23
- 지역별: 서울 988, 경기 174

## 미완료
- HIRA `--skip-detail` 모드로만 수집해서 `departments`, `bed_count`, `specialty` 컬럼이 비어있음. 이메일 있는 병원만 상세정보를 보강하는 스크립트는 논의만 되고 미구현
- 네이버 수집의 경기도 커버리지가 제한적 — 31개 시/군 중 6개만 구 단위 세부수집. 나머지는 시 단위 5건씩만
- `all_hospitals_with_email.csv`에서 `sido` 컬럼이 HIRA("서울")와 네이버("서울특별시")로 불일치. 정규화 미처리
- output 파일들이 `.gitignore`에 없어서 커밋 시 주의 필요

## 결정 사항
- **HIRA + 네이버 하이브리드 접근**: HIRA API가 치과의원(전국 246건), 경기도 데이터가 심각하게 부실하여 네이버 지역검색으로 보완. 네이버는 쿼리당 5건 제한이지만 동 단위로 쪼개서 커버리지 확보
- **종별코드 분리 처리**: 치과(49)→치과의원(41)/치과병원(21), 한방(80)→한의원(51)/한방병원(28)은 dgsbjtCd 필터 없이 종별 전체 조회
- **skip-detail 우선**: HIRA API 일일 1,000건 제한 때문에 상세정보(진료과목/병상) 생략하고 목록 수집 우선
- **cleanup 블록리스트**: cashdoc.me, gabia.com, sentry.io, interactivy.com, daangn.com 등 포털/호스팅/플랫폼 이메일 필터링

## 주의 사항
- HIRA API 일일 한도 1,000건 (개발 키). `--skip-detail`이면 목록 수집만 하므로 호출 수 적음. 상세정보는 병원당 2회 추가 호출
- 네이버 지역검색 API 일일 25,000건 한도. display=5, start=1 고정 (페이징 불가)
- `.env`에 `HIRA_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 3개 키 필요
- Step 2(URL 보강)가 병목 — 병원당 ~1초 소요. 수천 건이면 수시간
- `output/` 폴더의 CSV는 중간 결과물 포함하여 여러 개 존재. 최종 결과물은 `all_hospitals_with_email.csv`

## 다음 단계
1. `sido` 컬럼 정규화 ("서울특별시" → "서울", "경기도" → "경기") in `merge_and_cleanup.py`
2. 이메일 있는 병원만 HIRA 상세정보 보강 스크립트 구현 (departments, bed_count 채우기)
3. 경기도 나머지 25개 시/군 동단위 네이버 세부수집 확대
4. output 폴더 .gitignore 처리
5. 커밋 + 푸시

## 관련 파일
- `src/config.py` — 전체 설정 (API URL/키, 종별코드, 진료과목, 우선순위 그룹, 경로)
- `src/main.py` — HIRA 파이프라인 오케스트레이터
- `src/hira_client.py` — HIRA API 클라이언트
- `src/naver_client.py` — 네이버 지역검색 API 클라이언트 (신규)
- `src/naver_collect.py` — 네이버 구/시 단위 수집 (신규)
- `src/naver_collect_detail.py` — 네이버 동/구 단위 세부 수집 (신규)
- `src/naver_crawl_emails.py` — 네이버 데이터 이메일 크롤링 (신규)
- `src/merge_and_cleanup.py` — HIRA+네이버 합산 및 cleanup (신규)
- `src/step1_collect.py` — HIRA Step 1 (치과/한방 별도 종별 로직 추가)
- `src/email_crawler.py` — 웹사이트 이메일 추출
- `src/url_enricher.py` — 네이버 웹검색으로 URL 보강
- `src/cleanup.py` — 포털/호스팅 이메일 필터링
- `output/all_hospitals_with_email.csv` — 최종 결과 (이메일 있는 건만)
- `output/all_hospitals_merged.csv` — 전체 합산 데이터
- `.env` — API 키 3개 (HIRA, 네이버 ID/Secret)
