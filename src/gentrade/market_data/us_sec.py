"""
SEC EDGAR API Client

This module provides a comprehensive client for interacting with the SEC EDGAR API,
enabling retrieval of US stock data, company profiles, financial filings, and
detailed XBRL financial information. It handles API authentication, rate limiting,
and response parsing to deliver structured data for financial analysis.

Key features:
- Fetch complete list of US stocks with ticker symbols and CIK identifiers
- Retrieve company profiles including contact information and industry codes
- Access filing history (submissions) like 10-K, 10-Q, and 8-K forms
- Get detailed financial facts and concepts using XBRL data
- Retrieve aggregated industry data (frames) for benchmarking

Usage requires a valid User-Agent header with contact information as mandated by
the SEC. For more details on the SEC API, see: https://www.sec.gov/edgar/sec-api-documentation
"""
import time
from typing import List, Dict, Optional
import requests
import pandas as pd


class SECStockRetriever:
    """
    A client class for interacting with the SEC EDGAR API to retrieve stock data,
    company information, financial filings, and XBRL financial data.

    Handles API authentication through required headers, enforces rate limits,
    and parses responses into structured dictionaries for easy consumption.
    """

    # SEC API endpoints
    SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{}.json"
    SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"
    SEC_COMPANY_CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{}/{}/{}.json"
    SEC_FRAMES_URL = "https://data.sec.gov/api/xbrl/frames/{}/{}/{}.json"

    def __init__(self, user_agent: str):
        """
        Initialize the SECStockRetriever with required headers.

        The User-Agent must include your contact information (name and email) as
        mandated by the SEC to identify API users and prevent abuse.

        Args:
            user_agent: String with contact info (e.g., "John Doe john@example.com")
        """
        self.headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
            "Connection": "keep-alive",
            "Origin": "https://www.sec.gov",
            "Referer": "https://www.sec.gov/"
        }
        self.stocks = []
        self._rate_limit_delay = 1.0  # 1 second between requests to respect SEC limits

    def fetch_all_stocks(self) -> List[Dict]:
        """
        Fetch a complete list of US stocks from the SEC's ticker registry.

        Retrieves all registered companies with their CIK (Central Index Key),
        ticker symbol, and company name. Stores results in the `stocks` attribute
        and returns them as a list of dictionaries.

        Returns:
            List of dictionaries containing:
                - cik (int): SEC's unique company identifier
                - ticker (str): Stock ticker symbol
                - name (str): Company name
        """
        try:
            print("Fetching stock data from SEC EDGAR API...")
            # Use appropriate host for ticker endpoint
            ticker_headers = self.headers.copy()
            ticker_headers["Host"] = "www.sec.gov"

            response = requests.get(
                self.SEC_TICKERS_URL,
                headers=ticker_headers,
                timeout=30
            )

            response.raise_for_status()
            raw_data = response.json()

            self.stocks = [
                {
                    "cik": int(entry["cik_str"]),
                    "ticker": entry["ticker"],
                    "name": entry["title"]
                }
                for entry in raw_data.values()
            ]

            print(f"Successfully retrieved {len(self.stocks)} stocks")
            return self.stocks

        except Exception as e:
            print(f"Error fetching stocks: {str(e)}")
            return []

    def get_company_profile(self, cik: int) -> Optional[Dict]:
        """
        Retrieve detailed profile information for a specific company using its CIK.

        Provides company metadata including contact information, industry classification,
        and incorporation details.

        Args:
            cik: Central Index Key (SEC's unique identifier for the company)

        Returns:
            Dictionary containing company profile data with keys:
                - cik (int): Company's CIK
                - entity_name (str): Legal company name
                - sic_code (int): Standard Industrial Classification code
                - sic_description (str): Industry description
                - business_address (dict): Primary business location
                - mailing_address (dict): Mailing address
                - incorporation_state (str): State of incorporation
                - fiscal_year_end (str): Fiscal year end date (MMDD)
            None if retrieval fails or profile is not found.
        """
        formatted_cik = f"{cik:010d}"
        url = self.SEC_COMPANY_FACTS_URL.format(formatted_cik)

        try:
            time.sleep(self._rate_limit_delay)
            print(f"Fetching profile for CIK {formatted_cik}...")

            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 404:
                print(f"Profile not found for CIK {formatted_cik}")
                return None

            response.raise_for_status()
            raw_data = response.json()

            # Handle missing SIC description by using code lookup
            sic_code = raw_data.get("sic")
            sic_description = raw_data.get("sicDescription")

            # If description is missing but code exists, provide fallback
            if not sic_description and sic_code:
                sic_description = f"SIC Code {sic_code} (description unavailable)"

            return {
                "cik": cik,
                "entity_name": raw_data.get("entityName"),
                "sic_code": sic_code,
                "sic_description": sic_description,
                "business_address": self._extract_address(raw_data.get("businessAddress")),
                "mailing_address": self._extract_address(raw_data.get("mailingAddress")),
                "incorporation_state": raw_data.get("stateOfIncorporation"),
                "fiscal_year_end": raw_data.get("fiscalYearEnd")
            }

        except Exception as e:
            print(f"Error fetching profile: {str(e)}")
            return None

    def get_submissions(self, cik: int, limit: int = 50) -> Optional[Dict]:
        """
        Retrieve a company's filing history (submissions) from the SEC.

        Returns metadata about all SEC filings (like 10-K, 10-Q, 8-K) and details
        for the most recent filings, including direct links to documents.

        Args:
            cik: Central Index Key for the company
            limit: Maximum number of recent filings to return (default: 50)

        Returns:
            Dictionary containing:
                - cik (int): Company's CIK
                - entity_name (str): Company name
                - filings_count (int): Total number of filings
                - recent_filings (list): Recent filings with details including:
                    - form_type (str): Filing type (e.g., 10-K)
                    - filing_date (str): Date filed (YYYY-MM-DD)
                    - accession_number (str): SEC's unique filing identifier
                    - primary_document (str): Name of primary document
                    - filing_url (str): Direct URL to the document
            None if retrieval fails or no submissions are found.
        """
        formatted_cik = f"{cik:010d}"
        url = self.SEC_SUBMISSIONS_URL.format(formatted_cik)

        try:
            time.sleep(self._rate_limit_delay)
            print(f"Fetching submissions for CIK {formatted_cik}...")

            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 404:
                print(f"No submissions found for CIK {formatted_cik}")
                return None

            response.raise_for_status()
            raw_data = response.json()

            return {
                "cik": cik,
                "entity_name": raw_data.get("name"),
                "filings_count": len(raw_data.get("filings", {}).get("recent", {}).get("form", [])),
                "recent_filings": self._parse_filings(
                    raw_data.get("filings", {}).get("recent", {}),
                    limit,
                    cik  # Pass original CIK to use if response has empty value
                )
            }

        except Exception as e:
            print(f"Error fetching submissions: {str(e)}")
            return None

    def get_company_facts(self, cik: int) -> Optional[Dict]:
        """
        Retrieve all XBRL financial facts for a company from SEC filings.

        Provides comprehensive financial data organized by accounting taxonomy
        (e.g., US GAAP, IFRS) with standardized metrics, periods, and values.

        Args:
            cik: Central Index Key for the company

        Returns:
            Dictionary containing:
                - cik (int): Company's CIK
                - entity_name (str): Company name
                - facts (dict): Financial facts organized by taxonomy
                - taxonomies_available (list): Names of available taxonomies
            None if retrieval fails or no facts are found.
        """
        formatted_cik = f"{cik:010d}"
        url = self.SEC_COMPANY_FACTS_URL.format(formatted_cik)

        try:
            time.sleep(self._rate_limit_delay)
            print(f"Fetching financial facts for CIK {formatted_cik}...")

            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 404:
                print(f"No financial facts found for CIK {formatted_cik}")
                return None

            response.raise_for_status()
            raw_data = response.json()

            return {
                "cik": cik,
                "entity_name": raw_data.get("entityName"),
                "facts": raw_data.get("facts", {}),
                "taxonomies_available": list(raw_data.get("facts", {}).keys())
            }

        except Exception as e:
            print(f"Error fetching company facts: {str(e)}")
            return None

    def get_company_concept(self, cik: int, taxonomy: str, tag: str) -> Optional[Dict]:
        """
        Retrieve a specific XBRL financial concept for a company.

        Gets detailed information about a specific financial metric (e.g., net income)
        including metadata and time-series values with periods and units.

        Args:
            cik: Central Index Key for the company
            taxonomy: XBRL taxonomy (e.g., "us-gaap", "ifrs-full")
            tag: Financial concept tag (e.g., "NetIncomeLoss", "Assets")

        Returns:
            Dictionary containing:
                - cik (int): Company's CIK
                - entity_name (str): Company name
                - taxonomy (str): Taxonomy used
                - tag (str): Financial concept tag
                - label (str): Human-readable label for the tag
                - description (str): Detailed description of the concept
                - values (dict): Time-series values organized by unit
            None if retrieval fails or concept is not found.
        """
        formatted_cik = f"{cik:010d}"
        url = self.SEC_COMPANY_CONCEPT_URL.format(formatted_cik, taxonomy, tag)

        try:
            time.sleep(self._rate_limit_delay)
            print(f"Fetching {taxonomy}:{tag} for CIK {formatted_cik}...")

            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 404:
                print(f"No concept {tag} found for CIK {formatted_cik}")
                return None

            response.raise_for_status()
            raw_data = response.json()

            return {
                "cik": cik,
                "entity_name": raw_data.get("entityName"),
                "taxonomy": taxonomy,
                "tag": tag,
                "label": raw_data.get("label"),
                "description": raw_data.get("description"),
                "values": raw_data.get("units", {})
            }

        except Exception as e:
            print(f"Error fetching company concept: {str(e)}")
            return None

    def get_frames(self, taxonomy: str, tag: str, unit: str,
                  year: int, quarter: Optional[int] = None,
                  instantaneous: bool = False) -> Optional[Dict]:
        """
        Retrieve aggregated XBRL frame data across companies for benchmarking.

        Gets aggregated financial data for a specific metric across multiple companies
        for a given period, useful for industry comparisons and market analysis.

        Args:
            taxonomy: XBRL taxonomy (e.g., "us-gaap")
            tag: Financial concept tag (e.g., "NetIncomeLoss")
            unit: Unit of measure (e.g., "USD", "shares")
            year: Fiscal year (e.g., 2023)
            quarter: Optional fiscal quarter (1-4). If None, retrieves annual data.
            instantaneous: Whether the measure is instantaneous (point in time)
                rather than duration-based (over a period).

        Returns:
            Dictionary containing:
                - taxonomy (str): Taxonomy used
                - tag (str): Financial concept tag
                - unit (str): Unit of measure
                - period (str): Period (YYYY or YYYYQ#)
                - frame_type (str): "instantaneous" or "duration"
                - count (int): Number of companies in the frame
                - data (list): Aggregated data points with CIKs and values
            None if retrieval fails or no frame data is found.
        """
        # Build period parameter (YYYYQ# for quarters, YYYY for annual)
        period = f"{year}Q{quarter}" if quarter else f"{year}"

        # Build frame type segment (instantaneous or duration)
        frame_type = "instantaneous" if instantaneous else "duration"

        # Construct complete URL
        url = self.SEC_FRAMES_URL.format(taxonomy, tag, f"{unit}/{frame_type}/{period}")

        try:
            time.sleep(self._rate_limit_delay)
            print(f"Fetching {taxonomy}:{tag} frame for {period}...")

            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 404:
                print(f"No frame data found for {taxonomy}:{tag} in {period}")
                return None

            response.raise_for_status()
            raw_data = response.json()

            return {
                "taxonomy": taxonomy,
                "tag": tag,
                "unit": unit,
                "period": period,
                "frame_type": frame_type,
                "count": raw_data.get("count"),
                "data": raw_data.get("data", [])
            }

        except Exception as e:
            print(f"Error fetching frames: {str(e)}")
            return None

    def _parse_filings(self, recent_filings: Dict, limit: int, cik: int) -> List[Dict]:
        """
        Helper method to parse raw filing data into a structured list.

        Converts the SEC's parallel lists of filing attributes into a list of
        dictionaries with meaningful keys and constructs direct URLs to filings.

        Args:
            recent_filings: Raw 'recent' filings data from SEC submissions response
            limit: Maximum number of filings to return
            cik: Original CIK to use if response has empty CIK value

        Returns:
            List of dictionaries with filing details
        """
        if not recent_filings:
            return []

        forms = recent_filings.get("form", [])
        dates = recent_filings.get("filingDate", [])
        access_nums = recent_filings.get("accessionNumber", [])
        primary_docs = recent_filings.get("primaryDocument", [])

        parsed = []
        for i in range(min(len(forms), limit)):
            # Clean accession number for URL construction
            access_num_clean = access_nums[i].replace("-", "")

            # Use original CIK if response CIK is empty (fixes int() error)
            response_cik = recent_filings.get("cik", "")
            use_cik = cik if not response_cik else int(response_cik)

            # Build direct URL to the primary document
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{use_cik}/{access_num_clean}/{primary_docs[i]}"
            )

            parsed.append({
                "form_type": forms[i],
                "filing_date": dates[i],
                "accession_number": access_nums[i],
                "primary_document": primary_docs[i],
                "filing_url": filing_url
            })

        return parsed

    def _extract_address(self, address_data: Optional[Dict]) -> Dict:
        """
        Helper method to extract and format address information.

        Converts raw address data from SEC responses into a consistent dictionary
        structure with standard address components.

        Args:
            address_data: Raw address data from SEC API response

        Returns:
            Dictionary with structured address information
        """
        if not address_data:
            return {}

        return {
            "street": address_data.get("street1"),
            "street2": address_data.get("street2"),
            "city": address_data.get("city"),
            "state": address_data.get("state"),
            "zip_code": address_data.get("zip"),
            "country": address_data.get("country")
        }

    def get_company_by_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Find company information by ticker symbol.

        Searches the previously fetched list of stocks (from fetch_all_stocks())
        to find a company's CIK and name using its ticker symbol.

        Args:
            ticker: Stock ticker symbol (case-insensitive)

        Returns:
            Dictionary with "cik", "ticker", and "name" if found; None otherwise
        """
        if not self.stocks:
            print("No stock data loaded. Call fetch_all_stocks() first.")
            return None

        ticker_lower = ticker.lower()
        for company in self.stocks:
            if company["ticker"].lower() == ticker_lower:
                return company

        print(f"No company found with ticker: {ticker}")
        return None

    def get_sp500_tickers_and_ciks(self):
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        # Now feed the HTML text into pandas
        tables = pd.read_html(resp.text)
        df = tables[0]  # first table is the current constituents list

        # Extract ticker + CIK (Wikipedia has a CIK column)
        result = df[['Symbol', 'CIK']].copy()
        result = result.dropna(subset=['Symbol', 'CIK'])
        result['CIK'] = result['CIK'].astype(str).str.zfill(10)
        result['Symbol'] = result['Symbol'].astype(str)

        return result


if __name__ == "__main__":
    # Replace with your actual contact information
    USER_AGENT = "Your Full Name your.email@example.com"

    retriever = SECStockRetriever(user_agent=USER_AGENT)
    retriever.fetch_all_stocks()

    # Demonstrate with Apple (AAPL) if found
    aapl = retriever.get_company_by_ticker("AAPL")
    if aapl:
        aapl_cik = aapl["cik"]

        # Example 1: Get company profile
        aapl_profile = retriever.get_company_profile(aapl_cik)
        if aapl_profile:
            print(f"\nProfile: {aapl_profile['entity_name']}")
            print(f"Industry: {aapl_profile['sic_description']}")

        # Example 2: Get recent filings
        aapl_submissions = retriever.get_submissions(aapl_cik, limit=3)
        if aapl_submissions:
            print(f"\nRecent filings for {aapl_submissions['entity_name']}:")
            for filing in aapl_submissions["recent_filings"]:
                print(f"{filing['form_type']} filed on {filing['filing_date']}")

        # Example 3: Get specific financial concept (Net Income)
        net_income = retriever.get_company_concept(aapl_cik, "us-gaap", "NetIncomeLoss")
        if net_income:
            print(f"\n{net_income['label']}: {net_income['description'][:100]}...")
