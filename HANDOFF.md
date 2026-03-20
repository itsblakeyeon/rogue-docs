# Handoff

## 목표
`문서/의료 PoC.md`를 `프로젝트/medical/`로 이동하고, 기존 CLAUDE.md와 중복 내용을 정리.

## 완료
- `문서/의료 PoC.md` → `프로젝트/medical/기획.md`로 이동 + 이름 변경
- `프로젝트/medical/CLAUDE.md` 정리:
  - 영업 진행 상황 섹션 → `기획.md` 참조로 대체 (중복 제거)
  - Who 섹션에 적합/부적합 대상 상세 분석은 `기획.md` 참고 추가

## 미완료
- 없음.

## 결정 사항
- **기획.md를 별도 파일로 유지**: CLAUDE.md는 Claude 작업 가이드(기술), 기획.md는 비즈니스 전략 문서로 성격이 다르므로 분리
- **파일명 `기획.md`로 변경**: `의료 PoC.md`보다 내용(GTM 전략, 타겟 분석, 영업 현황)에 맞는 이름

## 주의 사항
- `기획.md`에 영업 진행 상황(미팅 일정 등)이 있으므로, 영업 업데이트는 `기획.md`에서 관리
- `crawling/` 실행 시 `cd 프로젝트/medical/crawling/` 후 실행해야 함
- `.env` 파일은 `crawling/` 안에 있어야 함

## 다음 단계
1. 이메일 발송 파이프라인 구축 (크롤링 결과 → 제안서 발송)
2. `crawling/src/merge_and_cleanup.py`에서 sido 컬럼 정규화
3. 제안서 PDF/PPT 변환 방식 결정
4. 3/24(월) 레픽의원 미팅 준비

## 관련 파일
- `프로젝트/medical/기획.md` — 비즈니스 기획 문서 (GTM, 타겟 분석, 영업 현황)
- `프로젝트/medical/CLAUDE.md` — medical 프로젝트 기술 가이드 (이번 세션에서 중복 제거)
- `프로젝트/medical/제안서.html` — 15슬라이드 영업 제안서
- `프로젝트/medical/crawling/` — 병원 이메일 크롤링 파이프라인
