from unittest.mock import patch, Mock
import pytest
from gentrade.scraper.search import BaiduSearchScraper


@pytest.fixture
def scraper():
    """Fixture to provide a BaiduSearchScraper instance"""
    return BaiduSearchScraper()


def test_initialization(scraper):
    """Test scraper initialization sets up required components"""
    assert scraper.base_url == "https://www.baidu.com/s"
    assert len(scraper.user_agents) > 0
    assert hasattr(scraper, "storage")
    assert hasattr(scraper, "content_extractor")
    assert len(scraper.time_patterns) == 8  # Check all time patterns are loaded


# def test_get_random_headers(scraper):
#     """Test header generation contains required fields"""
#     headers = scraper._get_random_headers()
#     assert "User-Agent" in headers
#     assert headers["User-Agent"] in scraper.user_agents
#     assert "Accept" in headers
#     assert "Referer" in headers
#     assert headers["Referer"] == "https://www.baidu.com/"


@patch("gentrade.scraper.search.requests.get")
def test_search_basic(mock_get, scraper):
    """Test basic search functionality returns expected structure"""
    # Mock successful response with sample search results
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <div class="result c-container xpath-log">
            <h3 class="t"><a href="https://example.com/news1">Test Title 1</a></h3>
            <div class="c-abstract">Test summary 1</div>
            <div class="c-source">Example Source 2小时前</div>
        </div>
        <div class="result c-container xpath-log">
            <h3 class="t"><a href="https://example.com/news2">Test Title 2</a></h3>
            <div class="c-abstract">Test summary 2</div>
            <div class="c-source">Another Source 1天前</div>
        </div>
        <a class="n">下一页</a>
    </html>
    """
    mock_get.return_value = mock_response

    # Execute search
    results = scraper.search(query="test", limit=2, fetch_content=False)

    # Verify results structure
    assert len(results) == 2
    assert results[0]["title"] == "Test Title 1"
    assert results[0]["url"] == "https://example.com/news1"
    assert results[0]["summary"] == "Test summary 1"
    assert results[0]["source"] == "Example Source"
    assert results[0]["content"] == ""  # fetch_content=False

    # Verify request parameters
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["wd"] == "test"
    assert kwargs["params"]["pn"] == 0  # First page


@patch("gentrade.scraper.search.requests.get")
def test_search_with_limit(mock_get, scraper):
    """Test search respects result limit"""
    # Create mock response with 5 results
    result_html = """
    <div class="result c-container xpath-log">
        <h3 class="t"><a href="https://example.com/news{{i}}">Title {{i}}</a></h3>
        <div class="c-abstract">Summary {{i}}</div>
        <div class="c-source">Source {{i}} 1小时前</div>
    </div>
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = f"""
    <html>
        {''.join([result_html.replace('{{i}}', str(i)) for i in range(5)])}
        <a class="n">下一页</a>
    </html>
    """
    mock_get.return_value = mock_response

    # Request limit=3
    results = scraper.search(query="limit test", limit=3)
    assert len(results) == 3


@patch("gentrade.scraper.search.requests.get")
def test_search_pagination(mock_get, scraper):
    """Test search handles pagination correctly"""
    # Create two page responses
    page1_html = """
    <html>
        <div class="result c-container xpath-log">
            <h3 class="t"><a href="https://example.com/p1">Page 1 Result</a></h3>
        </div>
        <a class="n">下一页</a>
    </html>
    """
    page2_html = """
    <html>
        <div class="result c-container xpath-log">
            <h3 class="t"><a href="https://example.com/p2">Page 2 Result</a></h3>
        </div>
    </html>
    """

    # Configure mock to return different pages
    mock_get.side_effect = [
        Mock(status_code=200, text=page1_html),
        Mock(status_code=200, text=page2_html)
    ]

    # Search with limit=2 (needs 2 pages)
    results = scraper.search(query="pagination test", limit=2)
    assert len(results) == 2
    assert mock_get.call_count == 2  # Should call twice for two pages


@patch("gentrade.scraper.search.requests.get")
def test_search_failed_request(mock_get, scraper):
    """Test search handles HTTP errors gracefully"""
    mock_response = Mock()
    mock_response.status_code = 403  # Forbidden
    mock_get.return_value = mock_response

    results = scraper.search(query="failed request", limit=5)
    assert len(results) == 0  # No results on failure


@patch("gentrade.scraper.search.ArticleContentExtractor.extract_content")
@patch("gentrade.scraper.search.requests.get")
def test_fetch_content_flag(mock_get, mock_extract, scraper):
    """Test fetch_content flag controls content extraction"""
    # Basic result HTML
    mock_response = Mock(status_code=200, text="""
        <div class="result c-container xpath-log">
            <h3 class="t"><a href="https://example.com/content">Content Test</a></h3>
            <div class="c-source">Source 10分钟前</div>
        </div>
    """)
    mock_get.return_value = mock_response
    mock_extract.return_value = "Full article content"

    # With content fetching
    results_with_content = scraper.search(query="content test", fetch_content=True)
    assert results_with_content[0]["content"] == "Full article content"
    mock_extract.assert_called_once()

    # Without content fetching
    mock_extract.reset_mock()
    results_no_content = scraper.search(query="content test", fetch_content=False)
    assert results_no_content[0]["content"] == ""
    mock_extract.assert_not_called()


# def test_time_pattern_robustness(scraper):
#     """Test time parsing handles messy real-world formats"""
#     messy_formats = [
#         " 3小时 前 ",  # Extra spaces
#         "2023/ 08 / 15",  # Inconsistent spacing
#         "2023-05-06  09:45",  # Extra spaces
#         "5 天前",  # Space between number and unit
#         "2022年12月31日18:30",  # No space between date and time
#     ]

#     for time_str in messy_formats:
#         # Should not raise exceptions and return valid timestamp
#         timestamp = scraper._parse_time_to_timestamp(time_str)
#         assert isinstance(timestamp, int)
#         assert timestamp > 0  # Valid timestamp


@patch("gentrade.scraper.search.requests.get")
def test_search_no_results(mock_get, scraper):
    """Test search handles empty results gracefully"""
    mock_response = Mock(status_code=200, text="<html></html>")  # No results
    mock_get.return_value = mock_response

    results = scraper.search(query="no results possible", limit=5)
    assert len(results) == 0
