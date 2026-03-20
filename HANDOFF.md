# Handoff

## 목표
`rogue-docs`와 `rogue-code` 두 레포를 `rogue` 하나로 통합. 프로젝트 내 medical 관련 폴더 2개(`medical`, `medical-crawling`)도 하나로 합침.

## 완료
- `rogue-docs` → `rogue`로 이름 변경 (로컬 + GitHub)
- `rogue-code/medical-crawling`을 git subtree로 `rogue`에 합침 (히스토리 보존)
- `프로젝트/medical-crawling/` → `프로젝트/medical/crawling/`으로 이동
- `프로젝트/medical/`의 CLAUDE.md, HANDOFF.md를 두 프로젝트 내용 병합하여 재작성
- GitHub `rogue-code` 레포 삭제
- 로컬 `rogue-code/` 폴더 삭제
- 루트 CLAUDE.md 업데이트 (통합 레포 구조 반영)
- 모든 변경사항 커밋 + 푸시 완료

## 미완료
- 없음. 레포 통합 작업 전체 완료.

## 결정 사항
- **git subtree --squash 사용**: rogue-code 히스토리를 squash로 보존하면서 합침. 개별 커밋까지는 불필요하다고 판단
- **medical/crawling/ 하위 배치**: 크롤링 코드를 medical 프로젝트의 서브폴더로 넣음. 제안서 제작과 이메일 크롤링이 같은 프로젝트의 파이프라인이므로
- **CLAUDE.md/HANDOFF.md 병합**: 두 프로젝트의 컨텍스트를 하나로 합쳐 프로젝트 전체 그림을 볼 수 있도록 함

## 주의 사항
- `crawling/` 내 Python 코드의 경로 참조(`output/` 등)는 crawling 디렉토리 기준으로 작성됨. 실행 시 `cd 프로젝트/medical/crawling/` 후 실행해야 함
- `.env` 파일은 `crawling/` 안에 있어야 함 (HIRA_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)
- `crawling/.venv/`는 git에 포함되지 않음. 새 환경에서는 venv 재생성 필요

## 다음 단계
1. 이메일 발송 파이프라인 구축 (크롤링 결과 → 제안서 발송)
2. `crawling/src/merge_and_cleanup.py`에서 sido 컬럼 정규화 ("서울특별시" → "서울")
3. 제안서 PDF/PPT 변환 방식 결정
4. 구글 폼 응답 알림 설정

## 관련 파일
- `CLAUDE.md` — 루트 레포 구조 설명 (이번 세션에서 업데이트)
- `프로젝트/medical/CLAUDE.md` — medical 프로젝트 통합 가이드 (두 프로젝트 병합)
- `프로젝트/medical/HANDOFF.md` — medical 프로젝트 인수인계 (두 프로젝트 병합)
- `프로젝트/medical/crawling/` — rogue-code에서 이동된 크롤링 코드
- `프로젝트/medical/제안서.html` — 15슬라이드 영업 제안서
- `프로젝트/medical/website/` — therogues.xyz 웹사이트
