# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

서울경기권 의원/병원급 의료기관의 이메일 및 메타데이터를 수집하는 크롤링 파이프라인. 두 가지 데이터 소스를 사용한다:
1. **HIRA API** (건강보험심사평가원 공공 API) — 병원 목록 + 메타데이터
2. **네이버 지역검색 API** — HIRA에서 누락된 병원 보완 (특히 치과, 경기도)

## Commands

```bash
source .venv/bin/activate

# 테스트
python -m pytest tests/ -v
python -m pytest tests/test_email_crawler.py -v -k "test_extract_emails"  # 단일 테스트

# HIRA 파이프라인 (우선순위 그룹별)
python src/main.py --priority 1 --skip-detail   # 피부과+성형외과
python src/main.py --priority 2 --skip-detail   # 치과+안과
python src/main.py --priority 3 --skip-detail   # 내과+가정의학과
python src/main.py --priority 4 --skip-detail   # 정형외과+재활의학과
python src/main.py --priority 5 --skip-detail   # 한방내과
python src/main.py --dept 14 --skip-detail       # 특정 과목만

# HIRA 개별 단계 실행
python src/main.py --step 1 --priority 1 --skip-detail  # 목록만
python src/main.py --step 2                               # URL 보강만
python src/main.py --step 3                               # 이메일 크롤링만

# 네이버 수집 (구/시 단위)
python src/naver_collect.py                    # 전체
python src/naver_collect.py --dept 치과         # 특정 과목만
python src/naver_collect.py --region 서울       # 특정 지역만

# 네이버 세부 수집 (동/구 단위, 더 세밀한 커버리지)
python src/naver_collect_detail.py             # 전체
python src/naver_collect_detail.py --target seoul  # 서울만

# 네이버 이메일 크롤링
python src/naver_crawl_emails.py

# 결과 클렌징 + 합산
python src/cleanup.py                          # HIRA 데이터만
python src/merge_and_cleanup.py                # HIRA + 네이버 합산
```

## Architecture

두 가지 데이터 파이프라인이 있으며, 최종적으로 `merge_and_cleanup.py`로 합산한다.

```
[HIRA 파이프라인]
Step 1 (hira_client → step1_collect)
  HIRA API로 병원 기본 목록 수집 → output/step1_hospitals_raw.csv
  ↓
Step 2 (url_enricher → step2_enrich_urls)
  홈페이지 URL이 없는 병원을 네이버 검색으로 보강 → output/step2_hospitals_with_urls.csv
  ↓
Step 3 (email_crawler → step3_crawl_emails)
  각 병원 웹사이트에서 이메일+대표원장명 추출 → output/step3_hospitals_final.csv
  ↓
cleanup.py → output/step3_hospitals_final_clean.csv

[네이버 파이프라인]
naver_collect.py (구/시 단위) + naver_collect_detail.py (동/구 단위)
  네이버 지역검색 API로 병원 목록 수집 → output/naver_hospitals.csv
  ↓
naver_crawl_emails.py
  웹사이트에서 이메일 추출 → output/naver_hospitals_with_email.csv

[합산]
merge_and_cleanup.py
  HIRA + 네이버 중복 제거 + 포털이메일 필터링
  → output/all_hospitals_merged.csv (전체)
  → output/all_hospitals_with_email.csv (이메일 있는 건만)
```

### 주요 모듈
- `config.py`: 모든 설정 상수 (API URL/키, 지역/종별/진료과목 코드, 우선순위 그룹, 경로)
- `main.py`: HIRA 파이프라인 오케스트레이터 (subprocess로 step 순차 실행)
- `hira_client.py`: HIRA API 클라이언트 (병원 목록, 진료과목, 병상 수)
- `naver_client.py`: 네이버 지역검색 API 클라이언트
- `url_enricher.py`: 네이버 웹검색으로 병원 URL 보강
- `email_crawler.py`: 웹사이트에서 이메일 + 대표원장명 추출
- `cleanup.py`: 포털/호스팅/플랫폼 이메일 필터링
- 각 src 모듈은 `sys.path.insert`로 src 디렉토리를 경로에 추가하여 `from config import ...` 형태로 임포트

## API 제약

### HIRA API
- 키: `.env`의 `HIRA_API_KEY` (data.go.kr 발급)
- 일일 호출 한도: **1,000건** (개발 단계)
- `--skip-detail`로 기본 목록만 수집하면 호출 수 절약
- 병원정보서비스(hospInfoServicev2)와 의료기관별상세정보서비스(MadmDtlInfoService2.7) 두 API를 각각 활용신청 필요
- **한계**: 치과의원(41) 전국 246건뿐, 경기도 데이터 부실. 의원(31) 종별만 데이터 풍부

### 네이버 지역검색 API
- 키: `.env`의 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` (developers.naver.com 발급)
- 일일 호출 한도: **25,000건**
- **한계**: 쿼리당 최대 5건, 페이징 불가 → 동 단위로 쪼개서 커버리지 확보

## 진행 상황

### HIRA 수집 (1~5순위 전체 완료)
1. 피부과(14), 성형외과(08) — **완료**
2. 치과(49), 안과(13) — **완료**
3. 내과(01), 가정의학과(23) — **완료**
4. 정형외과(06), 재활의학과(21) — **완료**
5. 한방내과(80) — **완료**

### 네이버 수집 (전체 완료)
- 서울 25구 + 경기 31시군 × 9개 진료과목 (구/시 단위)
- 서울 25구 동 단위 + 경기 6개 시 구 단위 (세부 수집)
- 이메일 크롤링 완료

### 최종 결과 (2026-03-19)
- 총 병원: 14,196건
- 유효 이메일: 1,175건 (HIRA 583 + 네이버 592)
- 지역: 서울 988건, 경기 174건
