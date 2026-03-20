import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.url_enricher import UrlEnricher


SAMPLE_NAVER_HTML = """
<html>
<body>
<div class="search_result">
  <a href="https://blog.naver.com/some_blog" class="link">블로그</a>
  <a href="https://www.naver.com" class="link">네이버</a>
  <a href="https://www.seoulclinic.co.kr" class="link">서울내과의원 홈페이지</a>
  <a href="https://cafe.naver.com/somecafe" class="link">카페</a>
</div>
</body>
</html>
"""


class TestBuildSearchQuery:
    def test_build_search_query(self):
        enricher = UrlEnricher()
        query = enricher.build_search_query("서울내과의원", "서울특별시 강남구")
        assert "서울내과의원" in query
        assert "강남구" in query
        assert "홈페이지" in query


class TestIsPortalUrl:
    @pytest.mark.parametrize("url", [
        "https://www.naver.com/something",
        "https://search.naver.com/search.naver?query=test",
        "https://blog.naver.com/mypost",
        "https://cafe.naver.com/mycafe",
        "https://www.kakao.com/hospital",
        "https://www.daum.net/search",
        "https://blog.daum.net/mypost",
        "https://cafe.daum.net/mycafe",
        "https://myblog.tistory.com/123",
        "https://something.modoo.at",
    ])
    def test_skip_portal_urls(self, url):
        enricher = UrlEnricher()
        assert enricher.is_portal_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://www.seoulclinic.co.kr",
        "https://hospital.example.com",
        "http://www.mydoctor.kr",
    ])
    def test_non_portal_urls(self, url):
        enricher = UrlEnricher()
        assert enricher.is_portal_url(url) is False


class TestExtractUrlFromNaverSearchHtml:
    @patch("src.url_enricher.requests.get")
    def test_extract_url_from_naver_search_html(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = SAMPLE_NAVER_HTML
        mock_get.return_value = mock_response

        enricher = UrlEnricher(delay=0)
        url = enricher.search_hospital_url("서울내과의원", "서울특별시 강남구")
        assert url == "https://www.seoulclinic.co.kr"

    @patch("src.url_enricher.requests.get")
    def test_search_returns_none_when_no_valid_url(self, mock_get):
        html = """
        <html><body>
        <a href="https://blog.naver.com/post">블로그</a>
        <a href="https://www.naver.com">네이버</a>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_get.return_value = mock_response

        enricher = UrlEnricher(delay=0)
        url = enricher.search_hospital_url("테스트의원", "서울특별시")
        assert url is None


class TestValidateUrl:
    @patch("src.url_enricher.requests.head")
    def test_validate_url_success(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        enricher = UrlEnricher()
        assert enricher.validate_url("https://www.seoulclinic.co.kr") is True
        mock_head.assert_called_once_with(
            "https://www.seoulclinic.co.kr",
            timeout=5,
            headers={"User-Agent": enricher.user_agent},
        )

    @patch("src.url_enricher.requests.head")
    def test_validate_url_failure_status(self, mock_head):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        enricher = UrlEnricher()
        assert enricher.validate_url("https://www.nonexistent.com") is False

    @patch("src.url_enricher.requests.head", side_effect=Exception("timeout"))
    def test_validate_url_exception(self, mock_head):
        enricher = UrlEnricher()
        assert enricher.validate_url("https://www.broken.com") is False


class TestEnrichUrls:
    @patch.object(UrlEnricher, "validate_url", return_value=True)
    @patch.object(UrlEnricher, "search_hospital_url", return_value="https://www.found.com")
    def test_enrich_urls_fills_missing_websites(self, mock_search, mock_validate):
        enricher = UrlEnricher(delay=0)
        df = pd.DataFrame({
            "yadmNm": ["서울내과의원", "강남병원"],
            "addr": ["서울특별시 강남구", "서울특별시 서초구"],
            "website": ["", "https://www.existing.com"],
        })
        result = enricher.enrich_urls(df)
        assert result.loc[0, "website"] == "https://www.found.com"
        assert result.loc[1, "website"] == "https://www.existing.com"
        mock_search.assert_called_once_with("서울내과의원", "서울특별시 강남구")

    @patch.object(UrlEnricher, "validate_url", return_value=False)
    @patch.object(UrlEnricher, "search_hospital_url", return_value="https://www.invalid.com")
    def test_enrich_urls_skips_invalid(self, mock_search, mock_validate):
        enricher = UrlEnricher(delay=0)
        df = pd.DataFrame({
            "yadmNm": ["테스트의원"],
            "addr": ["서울특별시"],
            "website": [""],
        })
        result = enricher.enrich_urls(df)
        assert result.loc[0, "website"] == ""

    @patch.object(UrlEnricher, "search_hospital_url", return_value=None)
    def test_enrich_urls_handles_nan(self, mock_search):
        enricher = UrlEnricher(delay=0)
        df = pd.DataFrame({
            "yadmNm": ["테스트의원"],
            "addr": ["서울특별시"],
            "website": [None],
        })
        result = enricher.enrich_urls(df)
        assert pd.isna(result.loc[0, "website"]) or result.loc[0, "website"] == ""
