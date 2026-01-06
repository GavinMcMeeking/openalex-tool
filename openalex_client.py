"""
OpenAlex API client module.
Handles API interactions, query building, and pagination.
"""

import time
import sys
import requests
from typing import List, Dict, Optional, Any
from urllib.parse import urlencode


BASE_URL = "https://api.openalex.org/works"
INSTITUTIONS_URL = "https://api.openalex.org/institutions"
AUTHORS_URL = "https://api.openalex.org/authors"
DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 200
DEFAULT_MAX_RESULTS = 100

# Cache for CSU institution ID
_CSU_ID_CACHE = None


class OpenAlexAPIError(Exception):
    """Custom exception for OpenAlex API errors."""
    pass


class RateLimitError(OpenAlexAPIError):
    """Exception raised when rate limit is exceeded."""
    pass


def lookup_institution_id(institution_name: str, email: Optional[str] = None) -> Optional[str]:
    """
    Look up institution ID by name.
    
    Args:
        institution_name: Institution display name
        email: Email for polite pool
        
    Returns:
        Institution OpenAlex ID URL or None if not found
    """
    params = {
        "filter": f"display_name.search:{institution_name}",
        "per_page": 1
    }
    if email:
        params["mailto"] = email
    
    try:
        response = make_request(INSTITUTIONS_URL, params)
        results = response.get("results", [])
        if results:
            return results[0].get("id")
    except Exception:
        pass
    
    return None


def lookup_csu_id(email: Optional[str] = None) -> Optional[str]:
    """
    Look up Colorado State University's institution ID.
    Uses caching to avoid repeated lookups.
    
    Args:
        email: Email for polite pool
        
    Returns:
        CSU institution ID URL or None if not found
    """
    global _CSU_ID_CACHE
    
    if _CSU_ID_CACHE is not None:
        return _CSU_ID_CACHE
    
    csu_id = lookup_institution_id("Colorado State University", email)
    _CSU_ID_CACHE = csu_id
    return csu_id


def get_csu_author_ids(email: Optional[str] = None, max_authors: int = 1000) -> List[str]:
    """
    Get all author IDs whose last known institution is Colorado State University.
    
    Args:
        email: Email for polite pool
        max_authors: Maximum number of authors to retrieve (for performance)
        
    Returns:
        List of author ID URLs
    """
    csu_id = lookup_csu_id(email)
    if not csu_id:
        return []
    
    author_ids = []
    page = 1
    per_page = 200  # Max per page for authors endpoint
    
    while len(author_ids) < max_authors:
        params = {
            "filter": f"last_known_institutions.id:{csu_id}",
            "per_page": per_page,
            "page": page,
            "select": "id"  # Only get IDs to save bandwidth
        }
        if email:
            params["mailto"] = email
        
        try:
            response = make_request(AUTHORS_URL, params)
            results = response.get("results", [])
            if not results:
                break
            
            for author in results:
                author_id = author.get("id")
                if author_id:
                    author_ids.append(author_id)
            
            # Check if there are more pages
            meta = response.get("meta", {})
            count = meta.get("count", 0)
            if len(author_ids) >= count or len(author_ids) >= max_authors:
                break
            
            page += 1
            time.sleep(0.1)  # Be polite
            
        except Exception as e:
            print(f"Warning: Error fetching CSU authors: {e}", file=sys.stderr)
            break
    
    return author_ids[:max_authors]


def lookup_author_id(author_name: str, email: Optional[str] = None) -> Optional[str]:
    """
    Look up author ID by name.
    
    Args:
        author_name: Author display name
        email: Email for polite pool
        
    Returns:
        Author OpenAlex ID URL or None if not found
    """
    params = {
        "filter": f"display_name.search:{author_name}",
        "per_page": 1
    }
    if email:
        params["mailto"] = email
    
    try:
        response = make_request(AUTHORS_URL, params)
        results = response.get("results", [])
        if results:
            return results[0].get("id")
    except Exception:
        pass
    
    return None


def normalize_author_id(author_id: str) -> str:
    """
    Normalize author ID to OpenAlex format.
    
    Supports:
    - OpenAlex ID: A1234567890
    - ORCID: 0000-0002-1825-0097 or https://orcid.org/0000-0002-1825-0097
    
    Args:
        author_id: Author identifier in various formats
        
    Returns:
        Normalized OpenAlex ID or ORCID URL
    """
    author_id = author_id.strip()
    
    # If it's already an OpenAlex ID (starts with A)
    if author_id.startswith("A") and author_id[1:].isdigit():
        return author_id
    
    # If it's an ORCID (with or without URL)
    if "orcid.org" in author_id:
        # Extract ORCID from URL
        orcid = author_id.split("/")[-1]
        return f"https://orcid.org/{orcid}"
    elif author_id.replace("-", "").isdigit() and len(author_id.replace("-", "")) == 16:
        # Looks like an ORCID without URL
        return f"https://orcid.org/{author_id}"
    
    # Assume it's an OpenAlex ID
    return author_id


def build_query_params(
    search: Optional[str] = None,
    author_id: Optional[str] = None,
    author_ids: Optional[List[str]] = None,
    institution: Optional[str] = None,
    csu_only: bool = False,
    fields: Optional[List[str]] = None,
    sort: Optional[str] = None,
    per_page: int = DEFAULT_PER_PAGE,
    page: int = 1,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build query parameters for OpenAlex API request.
    
    Args:
        search: Text search query
        author_id: Author OpenAlex ID or ORCID
        institution: Institution name
        fields: List of fields to select
        per_page: Number of results per page
        page: Page number
        email: Email for polite pool
        
    Returns:
        Dictionary of query parameters
    """
    params = {}
    
    # Add email for polite pool
    if email:
        params["mailto"] = email
    
    # Text search
    if search:
        params["search"] = search
    
    # Build filter parameter
    filters = []
    
    # Handle author IDs (single or multiple)
    author_id_list = []
    if author_id:
        normalized_id = normalize_author_id(author_id)
        # Convert OpenAlex ID to full URL format if needed
        if normalized_id.startswith("A") and normalized_id[1:].isdigit():
            normalized_id = f"https://openalex.org/{normalized_id}"
        author_id_list.append(normalized_id)
    
    if author_ids:
        # Normalize all author IDs
        for aid in author_ids:
            normalized_id = normalize_author_id(aid)
            if normalized_id.startswith("A") and normalized_id[1:].isdigit():
                normalized_id = f"https://openalex.org/{normalized_id}"
            author_id_list.append(normalized_id)
    
    # Combine multiple author IDs with OR logic
    if author_id_list:
        if len(author_id_list) == 1:
            filters.append(f"authorships.author.id:{author_id_list[0]}")
        else:
            # Use pipe separator for OR logic
            author_ids_str = "|".join(author_id_list)
            filters.append(f"authorships.author.id:{author_ids_str}")
    
    if institution:
        # Look up institution ID by name
        inst_id = lookup_institution_id(institution, email)
        if inst_id:
            filters.append(f"authorships.institutions.id:{inst_id}")
        else:
            # If lookup fails, raise an error with helpful message
            raise ValueError(f"Institution '{institution}' not found. Please check the spelling or use an institution ID instead.")
    
    # Note: csu_only is handled in search_works() by getting CSU author IDs first
    # and then using them in the author_ids parameter, so we don't add a filter here
    
    if filters:
        params["filter"] = ",".join(filters)
    
    # Note: OpenAlex API doesn't support selecting nested fields like "authors"
    # We fetch all fields and filter in the formatter instead
    # Field selection is handled in formatter.py, not in API query
    
    # Sorting
    if sort:
        params["sort"] = sort
    
    # Pagination
    params["per_page"] = min(per_page, MAX_PER_PAGE)
    params["page"] = page
    
    return params


def make_request(url: str, params: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
    """
    Make HTTP request to OpenAlex API with retry logic.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        max_retries: Maximum number of retry attempts
        
    Returns:
        JSON response as dictionary
        
    Raises:
        RateLimitError: If rate limit is exceeded
        OpenAlexAPIError: For other API errors
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get("Retry-After", 60))
                if attempt < max_retries - 1:
                    time.sleep(retry_after)
                    continue
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds.")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise OpenAlexAPIError(f"API request failed: {str(e)}")
    
    raise OpenAlexAPIError("Max retries exceeded")


def search_works(
    search: Optional[str] = None,
    author_id: Optional[str] = None,
    author_ids: Optional[List[str]] = None,
    institution: Optional[str] = None,
    csu_only: bool = False,
    fields: Optional[List[str]] = None,
    sort: Optional[str] = None,
    max_results: int = DEFAULT_MAX_RESULTS,
    per_page: int = DEFAULT_PER_PAGE,
    email: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for works in OpenAlex API with automatic pagination.
    
    Args:
        search: Text search query
        author_id: Author OpenAlex ID or ORCID
        institution: Institution name
        fields: List of fields to select
        max_results: Maximum number of results (0 = all)
        per_page: Results per page
        email: Email for polite pool
        
    Returns:
        List of work objects
        
    Raises:
        OpenAlexAPIError: For API errors
    """
    all_results = []
    page = 1
    per_page = min(per_page, MAX_PER_PAGE)
    
    # Handle CSU-only filter: get all CSU authors first
    if csu_only:
        print("Finding authors whose last known institution is Colorado State University...")
        csu_author_ids = get_csu_author_ids(email, max_authors=5000)  # Get more authors
        if not csu_author_ids:
            print("Warning: No authors found with CSU as last known institution.", file=sys.stderr)
            return []
        
        print(f"Found {len(csu_author_ids)} CSU authors. Using their IDs to filter works...")
        # Add CSU author IDs to the author_ids list
        if author_ids:
            # Combine with existing author IDs (intersection - both conditions must be true)
            author_ids = [aid for aid in author_ids if aid in csu_author_ids]
            if not author_ids:
                print("No works found: specified authors are not CSU authors.", file=sys.stderr)
                return []
        else:
            # Use all CSU authors
            author_ids = csu_author_ids
    
    # Validate that at least one search parameter is provided
    if not any([search, author_id, author_ids, institution]):
        raise ValueError("At least one search parameter (search, author_id, author_ids, or institution) must be provided")
    
    # If we have many author IDs, we need to batch them (API has URL length limits)
    # OpenAlex supports up to 100 author IDs per filter with OR logic, but URL length
    # limits mean we need smaller batches (about 25-50 IDs per request)
    MAX_AUTHORS_PER_FILTER = 25
    
    if author_ids and len(author_ids) > MAX_AUTHORS_PER_FILTER:
        # Batch the author IDs and make multiple requests
        print(f"Batching {len(author_ids)} author IDs into groups of {MAX_AUTHORS_PER_FILTER}...")
        all_results = []
        
        for i in range(0, len(author_ids), MAX_AUTHORS_PER_FILTER):
            batch = author_ids[i:i + MAX_AUTHORS_PER_FILTER]
            print(f"Processing batch {i // MAX_AUTHORS_PER_FILTER + 1} ({len(batch)} authors)...")
            
            batch_results = search_works(
                search=search,
                author_id=None,
                author_ids=batch,
                institution=institution,
                csu_only=False,  # Already handled above
                fields=fields,
                sort=sort,
                max_results=max_results if max_results > 0 else 0,  # 0 = all
                per_page=per_page,
                email=email
            )
            
            all_results.extend(batch_results)
            
            # Check if we've reached max results
            if max_results > 0 and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break
        
        # Remove duplicates (same work might appear in multiple batches)
        seen_ids = set()
        unique_results = []
        for work in all_results:
            work_id = work.get("id")
            if work_id and work_id not in seen_ids:
                seen_ids.add(work_id)
                unique_results.append(work)
        
        return unique_results
    
    # Normal flow for smaller author lists
    while True:
        # Build query parameters
        params = build_query_params(
            search=search,
            author_id=author_id,
            author_ids=author_ids,
            institution=institution,
            csu_only=False,  # Already handled above if needed
            fields=fields,
            sort=sort,
            per_page=per_page,
            page=page,
            email=email
        )
        
        # Make API request
        response = make_request(BASE_URL, params)
        
        # Extract results
        results = response.get("results", [])
        if not results:
            break
        
        all_results.extend(results)
        
        # Check if we've reached the max results limit
        if max_results > 0 and len(all_results) >= max_results:
            all_results = all_results[:max_results]
            break
        
        # Check if there are more pages
        # If we got fewer results than requested, we're on the last page
        if len(results) < per_page:
            break
        
        # Also check metadata if available
        meta = response.get("meta", {})
        count = meta.get("count", 0)
        if count > 0 and len(all_results) >= count:
            break
        
        page += 1
        
        # Small delay to be polite
        time.sleep(0.1)
    
    return all_results

