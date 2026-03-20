# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

병원 대상 데이터 기반 마케팅 비즈니스. 크롤링으로 병원 이메일을 수집하고, 제안서를 제작하여 영업하는 프로젝트.

- **크롤링** (`crawling/`): 서울경기권 의원/병원급 의료기관의 이메일 및 메타데이터 수집
- **제안서** (`제안서.html`): 영업용 비즈니스 제안서 (병원 원장 대상, 15슬라이드 HTML)
- **웹사이트** (`website/`): 소개 웹사이트 (therogues.xyz 배포)
- **리서치** (`리서치_*.md`): 시장분석, 경쟁사, 팀 분석 문서

## What
- 최종 결과물: 영업용 비즈니스 제안서 PDF (병원 원장 대상, 범용)
    - 수정이 가능하도록 PPT나 피그마로 먼저 만들 것.
    - What보다 How를 강조하는 방향. "우리는 이렇게 일합니다 — 감이 아니라 숫자로."

## Why
- 창업 아이템으로 버티컬 AI 비즈니스를 보는 중, 우선은 의료 산업에 집중.
- 국내 병원 마케팅 시장 연간 1조~1.5조원 + 외국인 의료관광 폭증 (2025년 160만)
- 기존 대행사/에이전시는 성과 불투명, 매출 연결 추적 안함 → 데이터 기반 성장 파트너 포지셔닝 기회.

## Who (타겟 고객)
- **중견 피부과/성형외과** (의사 3~5명, 직원 20~50명, 월매출 5~10억)
- 이미 대행사를 쓰고 있을 확률 높음. 국내+해외 마케팅 모두 성장시키고 싶은 단계.
- 마케팅비 월 1,500~3,000만원 (매출의 10~20%) 지출 중.
- 1인 개원의는 지불 여력 부족, 대형 프랜차이즈는 자체 팀 보유 → 중견이 스윗스팟.
- 적합/부적합 대상 상세 분석은 `기획.md` 참고.

## How

### 포지셔닝
- 태그라인: **"감이 아니라 숫자로."**
- 서브카피: **"매출까지 보는 병원 성장 파트너"**
- 차별화 1: **사업을 직접 키워본 팀** (57억→280억) — 대행사가 아닌 성장 파트너
- 차별화 2: 전환 퍼널 전체(인지→상담→예약→내원→매출)를 데이터로 추적

### 서비스 구조
- **서비스 1: 국내 마케팅** — 네이버, SNS, 퍼포먼스 광고, 전환 퍼널 추적
- **서비스 2: 해외 마케팅** — 국적별 SNS, 인플루언서, 전환 퍼널 추적
- **도구** (퍼널 안에 자연스럽게 녹임) — 다국어 AI 챗봇, 예약 자동화, 데이터 대시보드

### 팀
- 연준현(Blake): 그로스 마케팅 + 프로덕트 빌딩 (CAC 50%↓, ROAS 174%p↑, MVP 3일 출시) / 고려대
- 신지훈(Ji Hoon): 세일즈 + 사업개발 + 재무 (MRR 0→6억, 전사 57억→280억, VC 심사역) / 경희대
- 이윤규: 소프트웨어 개발 (네이버 제페토(글로벌), 직방 / 고려대)
- 김영욱: 그로스 마케팅 + 프로덕트 빌딩 (미리디(일본), BAT, 플랜핏 / 연세대)

## 프로젝트 구조

```
projects/medical/
├── 제안서.html              # 메인 결과물 (15슬라이드 HTML 프레젠테이션)
├── website/                 # 소개 웹사이트 (therogues.xyz)
├── 리서치_*.md              # 리서치 소스 자료 5개
├── crawling/                # 병원 이메일 크롤링 파이프라인
│   ├── src/                 # Python 소스코드
│   ├── tests/               # 테스트
│   ├── docs/                # API 가이드, 계획 문서
│   ├── requirements.txt     # Python 의존성
│   ├── .env.example         # API 키 템플릿
│   └── .gitignore
├── CLAUDE.md                # 이 파일
└── HANDOFF.md               # 세션 간 인수인계
```

## 크롤링 파이프라인 (`crawling/`)

### 데이터 소스
1. **HIRA API** (건강보험심사평가원) — 병원 목록 + 메타데이터
2. **네이버 지역검색 API** — HIRA에서 누락된 병원 보완 (특히 치과, 경기도)

### Commands

```bash
cd crawling
source .venv/bin/activate

# 테스트
python -m pytest tests/ -v

# HIRA 파이프라인 (우선순위 그룹별)
python src/main.py --priority 1 --skip-detail   # 피부과+성형외과
python src/main.py --priority 2 --skip-detail   # 치과+안과

# 네이버 수집
python src/naver_collect.py                      # 전체
python src/naver_collect_detail.py               # 동/구 단위 세부

# 결과 합산
python src/merge_and_cleanup.py                  # HIRA + 네이버 합산
```

### Architecture

```
[HIRA 파이프라인]
Step 1 (hira_client → step1_collect) → output/step1_hospitals_raw.csv
Step 2 (url_enricher → step2_enrich_urls) → output/step2_hospitals_with_urls.csv
Step 3 (email_crawler → step3_crawl_emails) → output/step3_hospitals_final.csv
cleanup.py → output/step3_hospitals_final_clean.csv

[네이버 파이프라인]
naver_collect.py + naver_collect_detail.py → output/naver_hospitals.csv
naver_crawl_emails.py → output/naver_hospitals_with_email.csv

[합산]
merge_and_cleanup.py → output/all_hospitals_with_email.csv (최종)
```

### API 제약
- HIRA API: `.env`의 `HIRA_API_KEY`, 일일 1,000건
- 네이버 API: `.env`의 `NAVER_CLIENT_ID` + `NAVER_CLIENT_SECRET`, 일일 25,000건

## 제안서 편집 규칙
- **비주얼 우선**: 표 반복 지양. 큰 숫자 + 차트/아이콘 + 카드 레이아웃 선호
- **팀 프로필**: 이모지 없음, 영문이름 없음, 스킬 나열 없음, 대학 인라인, LinkedIn 뱃지(이름 옆)
- **김영욱 역할**: "그로스 마케팅 + 프로덕트 빌딩" (퍼포먼스 마케팅 아님)
- **이윤규 제페토**: "네이버 제페토"로 표기
- **CTA**: "무료 1시간 상담" (진단 리포트 아님)

## 영업 진행 상황
영업 현황 및 GTM 전략은 `기획.md` 참고.
