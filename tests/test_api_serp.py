import os
import requests
import pytest

# Get SerpAPI key from environment variable (critical: do NOT hardcode!)
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
# SerpAPI Google Search endpoint
SERPAPI_GOOGLE_ENDPOINT = "https://serpapi.com/search"


def test_google_search_basic():
    """Test basic Google Search via SerpAPI: verify request success and core fields."""
    # 1. Define search parameters (query: "Coffee", location: "Austin, Texas")
    params = {
        "engine": "google",  # Search engine (must be "google" for Google Search)
        "q": "Coffee",        # Search query
        "location": "Austin, Texas, United States",  # Target location
        "hl": "en",          # Language (English)
        "gl": "us",          # Country (United States)
        "api_key": SERPAPI_KEY  # Authenticate with SerpAPI key
    }

    # 2. Send request to SerpAPI
    response = requests.get(SERPAPI_GOOGLE_ENDPOINT, params=params, timeout=5)

    # 3. Validate response status and structure
    # Check if request succeeded (HTTP 200)
    assert response.status_code == 200, f"Request failed: Status code {response.status_code}"

    # Parse JSON response
    result = response.json()

    # Check if SerpAPI returned a "Success" status
    assert result.get("search_metadata", {}).get("status") == "Success", \
        f"SerpAPI request failed: {result.get('search_metadata', {}).get('status')}"

    # Check if core search information exists (total results, query)
    search_info = result.get("search_information", {})
    assert "total_results" in search_info, "Response missing 'total_results' in search_information"
    assert search_info.get("query_displayed") == "Coffee", \
        f"Displayed query mismatch: Expected 'Coffee', got {search_info.get('query_displayed')}"


def test_google_search_local_results():
    """Test Google Local Results (e.g., coffee shops) via SerpAPI."""
    params = {
        "engine": "google",
        "q": "Coffee",
        "location": "Austin, Texas, United States",
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY
    }

    response = requests.get(SERPAPI_GOOGLE_ENDPOINT, params=params, timeout=5)
    result = response.json()

    # 1. Verify local results exist (for "Coffee" query in Austin)
    local_results = result.get("local_results", {}).get("places", [])
    assert len(local_results) > 0, "No local results (coffee shops) found for Austin"

    # 2. Validate core fields of the first local result (e.g., Starbucks)
    first_place = local_results[0]
    required_fields = ["title", "address", "type", "gps_coordinates"]
    for field in required_fields:
        assert field in first_place, f"Local result missing required field: {field}"

    # 3. Check if the place type is relevant (e.g., "Coffee shop" or "Cafe")
    assert first_place.get("type") in ["Coffee shop", "Cafe"], \
        f"Local result type mismatch: Expected 'Coffee shop'/'Cafe', got {first_place.get('type')}"


def test_google_search_organic_results():
    """Test Google Organic Results (e.g., Wikipedia, Healthline) via SerpAPI."""
    params = {
        "engine": "google",
        "q": "Coffee",
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY
    }

    response = requests.get(SERPAPI_GOOGLE_ENDPOINT, params=params, timeout=5)
    result = response.json()

    # 1. Verify organic results exist
    organic_results = result.get("organic_results", [])
    assert len(organic_results) > 0, "No organic results found for 'Coffee' query"
    print(organic_results)
    # 2. Validate core fields of organic results (all results must have these)
    for idx, result_item in enumerate(organic_results, 1):
        assert "title" in result_item, f"Organic result {idx} missing 'title'"
        assert "link" in result_item, f"Organic result {idx} missing 'link'"
        assert "snippet" in result_item, f"Organic result {idx} missing 'snippet'"

    # 3. Check if Wikipedia (top organic result for "Coffee") is present
    has_wikipedia = any("Wikipedia" in item.get("title", "") for item in organic_results)
    assert has_wikipedia, "Wikipedia result not found in organic results (expected for 'Coffee')"


# Run tests if the file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
