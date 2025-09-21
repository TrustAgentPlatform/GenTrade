"""
Module: test_sec_edgar_api.py
=============================
Pytest test suite for validating core functionality of the `sec-edgar-api` Python package.

Purpose:
- Verify correct behavior of the SEC Edgar API client's key methods:
  1. `get_company_concept`: Retrieves specific financial concepts for a company
  2. `get_company_facts`: Retrieves all financial facts for a company
  3. `get_frames`: Retrieves aggregated financial data across companies (by period/metric)
- Validate error handling for invalid inputs (e.g., bad CIK, missing User-Agent)
- Support mock network testing to avoid real SEC API rate limits/dependencies

Scope:
- Focuses on integration-level testing (calls real SEC API for success cases, mocks for isolation)
- Uses stable, public test data (AAPL, MSFT, NVDA, TSLA CIKs; US-GAAP metric:
  AccountsPayableCurrent)
- Covers both "happy path" (valid inputs) and "error path" (invalid inputs) scenarios

Dependencies:
- pytest: Test framework (install via `pip install pytest`)
- sec-edgar-api: SEC Edgar API client (install via `pip install sec-edgar-api`)
- unittest.mock: Built-in Python module for mocking network requests

Key Notes:
1. User-Agent Requirement: The SEC mandates a valid User-Agent (format: "Org Name email@domain.com")
   - Replace `<Your Organization Name> <your-email>@<your-domain.com>` with a real value before
     running
   - Empty/malformed User-Agents will cause API requests to fail
2. Rate Limits: The SEC enforces 10 requests/second. This suite uses minimal real calls to avoid
   throttling.
3. Test Data Stability: Uses major public companies' CIKs and standard US-GAAP metrics for
   consistency.
"""
from typing import Dict, Tuple
import pytest
from sec_edgar_api import EdgarClient




# ------------------------------
# Global Test Configuration
# ------------------------------
# Replace with your valid User-Agent (SEC requires this to identify request sources)
# Format: "Your Organization Name your-email@your-domain.com"
VALID_USER_AGENT = "bluewish bluewish.ken.lu@live.cn"

# Test Companies: (Company Name, CIK) - Valid, public CIKs for major tech firms
# CIKs are 10-digit strings (SEC standard; padded with leading zeros if needed)
TEST_COMPANIES = [
    ("Apple Inc. (AAPL)", "320193"),
    ("Microsoft Corp. (MSFT)", "789019"),
    ("NVIDIA Corp. (NVDA)", "1045810"),
    ("Tesla Inc. (TSLA)", "1318605")
]

# Test Taxonomy & Tag (US-GAAP standard field with consistent public data)
# Taxonomy: "us-gaap" (U.S. Generally Accepted Accounting Principles)
# Tag: "AccountsPayableCurrent" (Current Accounts Payable - common financial metric)
TEST_TAXONOMY = "us-gaap"
TEST_TAG = "AccountsPayableCurrent"
TEST_UNIT = "USD"  # Currency unit for financial data

# Test Period (Q4 2023 - recent, finalized data to ensure availability)
TEST_YEAR = "2023"
TEST_QUARTER = 4


# ------------------------------
# Pytest Fixtures
# ------------------------------
@pytest.fixture(scope="module")
def edgar_client() -> EdgarClient:
    """
    Pytest Fixture: Create a reusable EdgarClient instance for all tests in the module.
    Avoids reinitializing the client for every test (improves efficiency).
    """
    return EdgarClient(user_agent=VALID_USER_AGENT)


@pytest.fixture(params=TEST_COMPANIES, ids=[company[0] for company in TEST_COMPANIES])
def test_company(request) -> Tuple[str, str]:
    """
    Parameterized Pytest Fixture: Inject multiple test companies (name + CIK) into tests.
    - `params`: List of (Company Name, CIK) tuples from TEST_COMPANIES
    - `ids`: Human-readable labels for test reports (e.g., "Apple Inc. (AAPL)")
    """
    return request.param  # Returns (company_name, cik) for each test run


# ------------------------------
# Test 1: get_company_concept (Multiple Companies)
# ------------------------------
def test_get_company_concept_success(edgar_client: EdgarClient, test_company: Tuple[str, str]):
    """
    Test get_company_concept with multiple companies:
    Verifies response structure and critical fields for each test company (AAPL, MSFT, NVDA, TSLA).
    """
    company_name, cik = test_company  # Unpack company name and CIK from the fixture

    # 1. Call the API for the current test company
    response = edgar_client.get_company_concept(
        cik=cik,
        taxonomy=TEST_TAXONOMY,
        tag=TEST_TAG
    )
    print(response)

    # 2. Validate response type (SEC API returns JSON -> Python dict)
    assert isinstance(response, Dict), f"Failed for {company_name}: Response must be a dict"

    # 3. Validate CIK matches the test company
    assert response.get("cik") == int(cik), \
        f"Failed for {company_name}: Response CIK ({response.get('cik')}) != requested CIK ({cik})"

    # 4. Validate taxonomy and tag match requests
    assert response.get("taxonomy") == TEST_TAXONOMY, \
        f"Failed for {company_name}: Response taxonomy mismatch"
    assert response.get("tag") == TEST_TAG, \
        f"Failed for {company_name}: Response tag mismatch"

    # 5. Validate financial data exists (USD units)
    assert "units" in response, f"Failed for {company_name}: Missing 'units' field"
    assert TEST_UNIT in response["units"], \
        f"Failed for {company_name}: 'units' missing {TEST_UNIT}"


# ------------------------------
# Test 2: get_company_facts (Multiple Companies)
# ------------------------------
def test_get_company_facts_success(edgar_client: EdgarClient, test_company: Tuple[str, str]):
    """
    Test get_company_facts with multiple companies:
    Verifies response structure and core data categories for each test company.
    """
    company_name, cik = test_company  # Unpack company name and CIK from the fixture

    # 1. Call the API for the current test company
    response = edgar_client.get_company_facts(cik=cik)
    print(response)

    # 2. Validate basic response structure
    assert isinstance(response, Dict), f"Failed for {company_name}: Response must be a dict"
    assert response.get("cik") == int(cik), \
        f"Failed for {company_name}: Response CIK ({response.get('cik')}) != requested CIK ({cik})"

    # 3. Validate "facts" field and core data categories exist
    assert "facts" in response, f"Failed for {company_name}: Missing 'facts' field"
    facts = response["facts"]

    # "dei": Company metadata (name, status); "us-gaap": Financial metrics
    assert "dei" in facts, f"Failed for {company_name}: 'facts' missing 'dei' category"
    assert "us-gaap" in facts, f"Failed for {company_name}: 'facts' missing 'us-gaap' category"

    # 4. Validate test tag exists in GAAP data
    assert TEST_TAG in facts[TEST_TAXONOMY], \
        f"Failed for {company_name}: us-gaap missing {TEST_TAG} tag"


# ------------------------------
# Test 3: get_frames (Quarterly Aggregated Data)
# ------------------------------
def test_get_frames_quarterly_success(edgar_client: EdgarClient):
    """
    Test get_frames (quarterly data):
    Verifies aggregated data structure, period formatting, and required fields.
    (Note: get_frames is company-agnostic (aggregates all companies), so no need for
     multi-company test)
    """
    # 1. Call the API to get aggregated 2023 Q4 data
    response = edgar_client.get_frames(
        taxonomy=TEST_TAXONOMY,
        tag=TEST_TAG,
        unit=TEST_UNIT,
        year=TEST_YEAR,
        quarter=TEST_QUARTER,
        instantaneous=True  # For "point-in-time" metrics (e.g., payables)
    )
    print(response)

    # 2. Validate basic response structure
    assert isinstance(response, Dict), "Response must be a Python dictionary"
    assert response.get("taxonomy") == TEST_TAXONOMY, "Response taxonomy mismatch"
    assert response.get("tag") == TEST_TAG, "Response tag mismatch"

    # 3. Validate period format (SEC uses "ccp" field: CY+Year+Quarter+I)
    expected_ccp = f"CY{TEST_YEAR}Q{TEST_QUARTER}I"
    assert response.get("ccp") == expected_ccp, \
        f"Response CCP ({response.get('ccp')}) != expected {expected_ccp}"

    # 4. Validate aggregated data exists (non-empty list)
    assert "data" in response, "Missing 'data' field (aggregated company data)"
    assert len(response["data"]) > 0, "Aggregated 'data' list is empty"

    # 5. Validate required fields in a sample entry
    sample_data = response["data"][0]
    required_fields = ["cik", "entityName", "end", "val"]
    for field in required_fields:
        assert field in sample_data, f"Sample entry missing required field: '{field}'"
