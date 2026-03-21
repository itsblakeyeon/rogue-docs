import pytest
from unittest.mock import patch, MagicMock
from src.hira_client import HiraClient


SAMPLE_HOSPITAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
  <body>
    <items>
      <item>
        <yadmNm>서울내과의원</yadmNm>
        <addr>서울특별시 강남구 테헤란로 123</addr>
        <telno>02-1234-5678</telno>
        <hospUrl>http://www.seoulclinic.com</hospUrl>
        <clCd>31</clCd>
        <clCdNm>의원</clCdNm>
        <sidoCd>110000</sidoCd>
        <sidoCdNm>서울</sidoCdNm>
        <sgguCd>110019</sgguCd>
        <sgguCdNm>강남구</sgguCdNm>
        <emdongNm>역삼동</emdongNm>
        <estbDd>20100315</estbDd>
        <ykiho>JDQ4MTk4MSM1MSMkMSMkMCMkNCMkMiMkMyMkMCMkMCMkNjEk</ykiho>
        <drTotCnt>3</drTotCnt>
      </item>
    </items>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>1</totalCount>
  </body>
</response>"""

SAMPLE_EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
  <body>
    <items/>
    <numOfRows>10</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>0</totalCount>
  </body>
</response>"""

SAMPLE_DEPARTMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
  <body>
    <items>
      <item><dgsbjtCd>01</dgsbjtCd><dgsbjtCdNm>내과</dgsbjtCdNm><dgsbjtPrSdrCnt>2</dgsbjtPrSdrCnt></item>
      <item><dgsbjtCd>23</dgsbjtCd><dgsbjtCdNm>가정의학과</dgsbjtCdNm><dgsbjtPrSdrCnt>1</dgsbjtPrSdrCnt></item>
    </items>
    <totalCount>2</totalCount>
  </body>
</response>"""

SAMPLE_BED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>00</resultCode><resultMsg>NORMAL SERVICE.</resultMsg></header>
  <body>
    <items>
      <item>
        <hghrSickbdCnt>5</hghrSickbdCnt>
        <stdSickbdCnt>20</stdSickbdCnt>
        <aduChldSprmCnt>3</aduChldSprmCnt>
        <chldSprmCnt>0</chldSprmCnt>
        <nbySprmCnt>0</nbySprmCnt>
      </item>
    </items>
    <totalCount>1</totalCount>
  </body>
</response>"""


@pytest.fixture
def client():
    return HiraClient(api_key="test_api_key")


# Task 2 Tests

class TestParseHospitalItem:
    def test_parse_hospital_item(self, client):
        """Given sample XML for one hospital item, parse_response returns correct dict."""
        result = client.parse_response(SAMPLE_HOSPITAL_XML)
        assert len(result) == 1
        item = result[0]
        assert item["yadmNm"] == "서울내과의원"
        assert item["addr"] == "서울특별시 강남구 테헤란로 123"
        assert item["telno"] == "02-1234-5678"
        assert item["hospUrl"] == "http://www.seoulclinic.com"
        assert item["clCdNm"] == "의원"
        assert item["sidoCdNm"] == "서울"
        assert item["sgguCdNm"] == "강남구"
        assert item["emdongNm"] == "역삼동"
        assert item["estbDd"] == "20100315"
        assert item["ykiho"] == "JDQ4MTk4MSM1MSMkMSMkMCMkNCMkMiMkMyMkMCMkMCMkNjEk"
        assert item["drTotCnt"] == "3"

    def test_parse_empty_response(self, client):
        """Given XML with totalCount=0, returns empty list."""
        result = client.parse_response(SAMPLE_EMPTY_XML)
        assert result == []

    def test_build_request_params(self, client):
        """build_params returns correct dict with all required keys."""
        params = client.build_params(sido_cd="110000", cl_cd="31", page=1)
        assert params["ServiceKey"] == "test_api_key"
        assert params["pageNo"] == 1
        assert params["numOfRows"] == 100
        assert params["sidoCd"] == "110000"
        assert params["clCd"] == "31"


# Task 3 Tests

class TestParseDepartmentInfo:
    def test_parse_department_info(self, client):
        """Parse department list from XML correctly."""
        result = client.parse_departments(SAMPLE_DEPARTMENT_XML)
        assert len(result) == 2
        assert result[0] == {"code": "01", "name": "내과", "doctor_count": 2}
        assert result[1] == {"code": "23", "name": "가정의학과", "doctor_count": 1}

    def test_parse_bed_info(self, client):
        """Sum up all bed count fields correctly."""
        result = client.parse_bed_count(SAMPLE_BED_XML)
        # 5 + 20 + 3 + 0 + 0 = 28
        assert result == 28

    def test_aggregate_departments(self, client):
        """Multiple departments joined as comma-separated string."""
        departments = [
            {"code": "01", "name": "내과", "doctor_count": 2},
            {"code": "23", "name": "가정의학과", "doctor_count": 1},
        ]
        result = client.aggregate_departments(departments)
        assert result == "내과, 가정의학과"
