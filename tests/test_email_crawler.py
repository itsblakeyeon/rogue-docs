import pytest
from unittest.mock import patch, MagicMock
from src.email_crawler import EmailCrawler


@pytest.fixture
def crawler():
    return EmailCrawler()


class TestExtractEmails:
    def test_extract_emails_from_html(self, crawler):
        html = '<p>문의: hospital@example.com</p><a href="mailto:info@clinic.kr">이메일</a>'
        result = crawler.extract_emails(html)
        assert result == {"hospital@example.com", "info@clinic.kr"}

    def test_extract_emails_from_mailto(self, crawler):
        html = '<a href="mailto:test@hospital.co.kr?subject=문의">연락</a>'
        result = crawler.extract_emails(html)
        assert result == {"test@hospital.co.kr"}

    def test_deduplicate_emails(self, crawler):
        html = "<p>info@test.com</p><p>info@test.com</p><p>info@test.com</p>"
        result = crawler.extract_emails(html)
        assert result == {"info@test.com"}

    def test_filter_invalid_emails(self, crawler):
        html = '<img src="banner@2x.png"><p>noreply@system.com</p><p>real@hospital.com</p>'
        result = crawler.extract_emails(html)
        assert result == {"real@hospital.com"}


class TestFindContactPages:
    def test_find_contact_page_links(self, crawler):
        html = """
        <a href="/about">소개</a>
        <a href="/contact">연락처</a>
        <a href="https://www.hospital.com/inquiry">문의</a>
        <a href="/location">오시는길</a>
        <a href="/greeting">인사말</a>
        <a href="/services">진료과목</a>
        <a href="/news">뉴스</a>
        """
        base_url = "https://www.hospital.com"
        result = crawler.find_contact_pages(html, base_url)
        assert "https://www.hospital.com/about" in result
        assert "https://www.hospital.com/contact" in result
        assert "https://www.hospital.com/inquiry" in result
        assert "https://www.hospital.com/location" in result
        assert "https://www.hospital.com/greeting" in result
        # Non-contact pages should not be included
        assert "https://www.hospital.com/services" not in result
        assert "https://www.hospital.com/news" not in result

    def test_find_contact_page_links_relative(self, crawler):
        html = '<a href="/contact">문의</a>'
        base_url = "https://www.hospital.com"
        result = crawler.find_contact_pages(html, base_url)
        assert result == ["https://www.hospital.com/contact"]


class TestExtractRepresentativeName:
    def test_extract_representative_name(self, crawler):
        html_cases = [
            ("<p>대표원장 : 김철수</p>", "김철수"),
            ("<span>원장 홍길동</span>", "홍길동"),
            ("<p>대표 : 이영희</p>", "이영희"),
        ]
        for html, expected in html_cases:
            result = crawler.extract_representative_name(html)
            assert result == expected, f"Failed for input: {html}"

    def test_extract_representative_name_not_found(self, crawler):
        html = "<p>병원 안내 페이지입니다.</p>"
        result = crawler.extract_representative_name(html)
        assert result is None


class TestCrawlHospital:
    @patch.object(EmailCrawler, "fetch_page")
    def test_crawl_hospital_with_emails_on_main_page(self, mock_fetch, crawler):
        mock_fetch.return_value = '<p>문의: contact@hospital.com</p><p>대표원장 : 김의사</p>'
        result = crawler.crawl_hospital("https://www.hospital.com")
        assert "contact@hospital.com" in result["emails"]
        assert result["representative"] == "김의사"

    @patch.object(EmailCrawler, "fetch_page")
    def test_crawl_hospital_follows_contact_pages(self, mock_fetch, crawler):
        main_html = '<a href="/contact">연락처</a><p>대표원장 : 박원장</p>'
        contact_html = "<p>이메일: info@hospital.com</p>"
        mock_fetch.side_effect = [main_html, contact_html]
        result = crawler.crawl_hospital("https://www.hospital.com")
        assert "info@hospital.com" in result["emails"]
        assert result["representative"] == "박원장"

    @patch.object(EmailCrawler, "fetch_page")
    def test_crawl_hospital_fetch_fails(self, mock_fetch, crawler):
        mock_fetch.return_value = None
        result = crawler.crawl_hospital("https://www.hospital.com")
        assert result["emails"] == []
        assert result["representative"] is None
