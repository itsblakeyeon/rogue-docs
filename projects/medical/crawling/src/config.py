import os
from dotenv import load_dotenv

load_dotenv()

# HIRA API
HIRA_API_KEY = os.getenv("HIRA_API_KEY", "")

# Naver Search API
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
HIRA_BASE_URL = "https://apis.data.go.kr/B551182/hospInfoServicev2"
HIRA_DETAIL_BASE_URL = "https://apis.data.go.kr/B551182/MadmDtlInfoService2.7"

# 지역 코드 (시도)
REGION_CODES = {
    "서울": "110000",
    "경기": "410000",
}

# 종별 코드 (clCd)
INSTITUTION_TYPES = {
    "의원": "31",
    "병원": "11",
    "치과의원": "41",
    "한의원": "51",
    "치과병원": "21",
    "한방병원": "28",
}

# 타겟 종별 (의원급 + 병원급)
TARGET_INSTITUTION_CODES = ["31", "11"]

# 진료과목 → 종별 매핑 (해당 진료과목은 별도 종별로 존재하므로 종별 전체 조회)
# 치과(49) → 치과의원(41), 치과병원(21) / 한방내과(80) → 한의원(51), 한방병원(28)
DEPT_TO_INSTITUTION_CODES = {
    "49": ["41", "21"],   # 치과 → 치과의원, 치과병원
    "80": ["51", "28"],   # 한방내과 → 한의원, 한방병원
}

# 진료과목 코드 (dgsbjtCd)
DEPARTMENT_CODES = {
    "피부과": "14",
    "성형외과": "08",
    "치과": "49",
    "안과": "13",
    "내과": "01",
    "가정의학과": "23",
    "정형외과": "06",
    "재활의학과": "21",
    "한방내과": "80",
}

# 우선순위별 타겟 진료과목 그룹
TARGET_DEPARTMENTS = {
    1: ["14", "08"],           # 피부과, 성형외과
    2: ["49", "13"],           # 치과, 안과
    3: ["01", "23"],           # 내과, 가정의학과
    4: ["06", "21"],           # 정형외과, 재활의학과
    5: ["80"],                 # 한방내과
}

# 요청 설정
REQUEST_DELAY = 0.1  # 초
REQUEST_TIMEOUT = 10  # 초
NUM_OF_ROWS = 100  # 페이지당 결과 수

# 네이버 검색 타겟 진료과목 (검색 키워드)
NAVER_SEARCH_DEPARTMENTS = [
    "피부과", "성형외과", "치과", "안과",
    "내과", "가정의학과", "정형외과", "재활의학과", "한의원",
]

# 출력 경로
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
STEP1_OUTPUT = os.path.join(OUTPUT_DIR, "step1_hospitals_raw.csv")
STEP2_OUTPUT = os.path.join(OUTPUT_DIR, "step2_hospitals_with_urls.csv")
STEP3_OUTPUT = os.path.join(OUTPUT_DIR, "step3_hospitals_final.csv")
EMAIL_OUTPUT = os.path.join(OUTPUT_DIR, "hospitals_with_email.csv")
NAVER_OUTPUT = os.path.join(OUTPUT_DIR, "naver_hospitals.csv")
LOG_FILE = os.path.join(OUTPUT_DIR, "crawl.log")
