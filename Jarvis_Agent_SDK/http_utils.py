#!/usr/bin/env python3
"""
HTTP Utilities for Jarvis Handlers

This module provides standardized HTTP client utilities for Jarvis handlers,
following the Model Context Protocol (MCP) patterns and best practices.

Features:
- Async HTTP client with proper connection management
- Standardized error handling and retries
- Authentication helpers
- Request/response logging
- Timeout and rate limiting
- Common patterns for external API integration

Usage:
    # Basic async HTTP request
    async with create_jarvis_http_client() as client:
        response = await client.get("https://api.example.com/data")
        
    # With authentication
    headers = {"Authorization": "Bearer token"}
    async with create_jarvis_http_client(headers=headers) as client:
        data = await client.get("/endpoint")
        
    # Using helper functions
    weather_data = await make_weather_request("New York")
    news_data = await make_news_request(category="technology")
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import httpx
from httpx import Timeout, Response

# Configure logging
logger = logging.getLogger(__name__)

# Default timeout configuration (following MCP patterns)
DEFAULT_TIMEOUT = Timeout(30.0, read=60.0)

# Rate limiting configuration
DEFAULT_RATE_LIMIT = {
    "requests_per_second": 10,
    "burst_limit": 20
}

# Common headers for Jarvis requests
DEFAULT_HEADERS = {
    "User-Agent": "Jarvis-Agent-System/1.0 (github.com/user/jarvis)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate"
}


class HttpError(Exception):
    """Custom exception for HTTP-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Response] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RateLimiter:
    """Simple rate limiter for HTTP requests."""
    
    def __init__(self, requests_per_second: float = 10, burst_limit: int = 20):
        self.requests_per_second = requests_per_second
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token for making a request."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.burst_limit,
                self.tokens + elapsed * self.requests_per_second
            )
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                # Calculate wait time
                wait_time = (1 - self.tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)
                self.tokens = 0
                return True


def create_jarvis_http_client(
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[Timeout] = None,
    auth: Optional[httpx.Auth] = None,
    rate_limiter: Optional[RateLimiter] = None,
    **kwargs
) -> httpx.AsyncClient:
    """
    Create a standardized httpx AsyncClient for Jarvis handlers.
    
    Following MCP patterns with Jarvis-specific defaults:
    - follow_redirects=True
    - Default timeout of 30 seconds (60s read timeout)
    - Standard Jarvis user agent
    - JSON content type preference
    
    Args:
        headers: Optional headers to include with all requests
        timeout: Request timeout as httpx.Timeout object
        auth: Optional authentication handler
        rate_limiter: Optional rate limiter for requests
        **kwargs: Additional arguments passed to httpx.AsyncClient
        
    Returns:
        Configured httpx.AsyncClient instance with Jarvis defaults
        
    Examples:
        # Basic usage
        async with create_jarvis_http_client() as client:
            response = await client.get("https://api.example.com")
            
        # With authentication
        headers = {"Authorization": "Bearer token"}
        async with create_jarvis_http_client(headers=headers) as client:
            response = await client.get("/protected")
            
        # With custom timeout and rate limiting
        timeout = Timeout(60.0, read=120.0)
        rate_limiter = RateLimiter(requests_per_second=5)
        async with create_jarvis_http_client(timeout=timeout, rate_limiter=rate_limiter) as client:
            response = await client.get("/slow-endpoint")
    """
    # Merge headers with defaults
    final_headers = DEFAULT_HEADERS.copy()
    if headers:
        final_headers.update(headers)
    
    # Set defaults
    client_kwargs = {
        "follow_redirects": True,
        "timeout": timeout or DEFAULT_TIMEOUT,
        "headers": final_headers,
        **kwargs
    }
    
    # Add authentication if provided
    if auth:
        client_kwargs["auth"] = auth
    
    # Create client
    client = httpx.AsyncClient(**client_kwargs)
    
    # Add rate limiter if provided
    if rate_limiter:
        client._jarvis_rate_limiter = rate_limiter
    
    return client


@asynccontextmanager
async def managed_http_client(
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[Timeout] = None,
    auth: Optional[httpx.Auth] = None,
    rate_limiter: Optional[RateLimiter] = None,
    **kwargs
):
    """
    Context manager for HTTP client with automatic cleanup.
    
    Args:
        headers: Optional headers
        timeout: Request timeout
        auth: Authentication handler
        rate_limiter: Rate limiter
        **kwargs: Additional client arguments
        
    Yields:
        httpx.AsyncClient: Configured HTTP client
        
    Example:
        async with managed_http_client() as client:
            response = await client.get("https://api.example.com")
            return response.json()
    """
    client = create_jarvis_http_client(
        headers=headers,
        timeout=timeout,
        auth=auth,
        rate_limiter=rate_limiter,
        **kwargs
    )
    try:
        yield client
    finally:
        await client.aclose()


async def make_request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    **kwargs
) -> Response:
    """
    Make an HTTP request with exponential backoff retry logic.
    
    Args:
        client: httpx.AsyncClient instance
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        max_retries: Maximum number of retry attempts
        backoff_factor: Backoff multiplier for retry delays
        **kwargs: Additional arguments passed to the request
        
    Returns:
        httpx.Response: The successful response
        
    Raises:
        HttpError: If all retries are exhausted or non-retryable error occurs
        
    Example:
        async with create_jarvis_http_client() as client:
            response = await make_request_with_retry(
                client, "GET", "https://api.example.com/data"
            )
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Apply rate limiting if available
            if hasattr(client, '_jarvis_rate_limiter'):
                await client._jarvis_rate_limiter.acquire()
            
            # Make the request
            response = await client.request(method, url, **kwargs)
            
            # Check for HTTP errors
            if response.status_code >= 500:
                # Server errors are retryable
                response.raise_for_status()
            elif response.status_code >= 400:
                # Client errors are generally not retryable
                raise HttpError(
                    f"HTTP {response.status_code}: {response.text}",
                    status_code=response.status_code,
                    response=response
                )
            
            # Success
            logger.debug(f"Request successful: {method} {url} -> {response.status_code}")
            return response
            
        except httpx.HTTPStatusError as e:
            last_error = e
            if attempt < max_retries and e.response.status_code >= 500:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise HttpError(
                    f"HTTP {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                    response=e.response
                )
                
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < max_retries:
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                continue
            else:
                raise HttpError(f"Request failed after {max_retries} retries: {e}")
    
    # This should never be reached, but just in case
    raise HttpError(f"Request failed after {max_retries} retries: {last_error}")


# Handler-specific HTTP helper functions following common patterns
async def make_weather_request(
    location: str,
    api_key: str,
    units: str = "metric",
    lang: str = "en"
) -> Dict[str, Any]:
    """
    Make a weather API request following the NWS pattern.
    
    Args:
        location: Location name or coordinates
        api_key: OpenWeather API key
        units: Temperature units (metric, imperial, standard)
        lang: Language code
        
    Returns:
        Dict containing weather data
        
    Raises:
        HttpError: If the request fails
        
    Example:
        weather_data = await make_weather_request("New York", api_key)
        temperature = weather_data["main"]["temp"]
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    
    async with managed_http_client(headers=headers) as client:
        # First geocode the location
        geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
        geocode_params = {
            "q": location,
            "appid": api_key,
            "limit": 1
        }
        
        geocode_response = await make_request_with_retry(
            client, "GET", geocode_url, params=geocode_params
        )
        geocode_data = geocode_response.json()
        
        if not geocode_data:
            raise HttpError(f"Location not found: {location}")
        
        lat, lon = geocode_data[0]["lat"], geocode_data[0]["lon"]
        
        # Get weather data
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        weather_params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": units,
            "lang": lang
        }
        
        weather_response = await make_request_with_retry(
            client, "GET", weather_url, params=weather_params
        )
        
        return weather_response.json()


async def make_news_request(
    api_key: str,
    query: Optional[str] = None,
    category: Optional[str] = None,
    country: str = "us",
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Make a news API request with standardized error handling.
    
    Args:
        api_key: News API key
        query: Search query
        category: News category
        country: Country code
        page_size: Number of articles to return
        
    Returns:
        Dict containing news data
        
    Example:
        news_data = await make_news_request(api_key, category="technology")
        articles = news_data["articles"]
    """
    headers = {"X-API-Key": api_key}
    
    async with managed_http_client(headers=headers) as client:
        if query:
            url = "https://newsapi.org/v2/everything"
            params = {"q": query, "pageSize": page_size, "sortBy": "relevancy"}
        else:
            url = "https://newsapi.org/v2/top-headlines"
            params = {"country": country, "pageSize": page_size}
            if category:
                params["category"] = category
        
        response = await make_request_with_retry(client, "GET", url, params=params)
        return response.json()


async def make_api_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    auth_token: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout_seconds: float = 30.0,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Generic API request helper with common authentication patterns.
    
    Args:
        url: API endpoint URL
        method: HTTP method
        headers: Custom headers
        params: Query parameters
        json_data: JSON payload for POST/PUT requests
        auth_token: Bearer token for Authorization header
        api_key: API key (added to headers as X-API-Key)
        timeout_seconds: Request timeout
        max_retries: Number of retry attempts
        
    Returns:
        Dict containing the JSON response
        
    Example:
        # With bearer token
        data = await make_api_request(
            "https://api.example.com/data",
            auth_token="your_token_here"
        )
        
        # With API key
        data = await make_api_request(
            "https://api.example.com/search",
            params={"q": "query"},
            api_key="your_key_here"
        )
    """
    request_headers = headers.copy() if headers else {}
    
    # Add authentication
    if auth_token:
        request_headers["Authorization"] = f"Bearer {auth_token}"
    if api_key:
        request_headers["X-API-Key"] = api_key
    
    timeout = Timeout(timeout_seconds)
    
    async with managed_http_client(headers=request_headers, timeout=timeout) as client:
        kwargs = {}
        if params:
            kwargs["params"] = params
        if json_data:
            kwargs["json"] = json_data
            
        response = await make_request_with_retry(
            client, method, url, max_retries=max_retries, **kwargs
        )
        
        try:
            return response.json()
        except Exception as e:
            raise HttpError(f"Failed to parse JSON response: {e}", response=response)


# Utility functions for common HTTP patterns
def get_auth_headers(token: str, token_type: str = "Bearer") -> Dict[str, str]:
    """
    Create authentication headers.
    
    Args:
        token: Authentication token
        token_type: Token type (Bearer, Basic, etc.)
        
    Returns:
        Dict with Authorization header
    """
    return {"Authorization": f"{token_type} {token}"}


def get_api_key_headers(api_key: str, header_name: str = "X-API-Key") -> Dict[str, str]:
    """
    Create API key headers.
    
    Args:
        api_key: API key value
        header_name: Header name for the API key
        
    Returns:
        Dict with API key header
    """
    return {header_name: api_key}


async def download_file(
    url: str,
    file_path: str,
    headers: Optional[Dict[str, str]] = None,
    chunk_size: int = 8192,
    progress_callback: Optional[callable] = None
) -> bool:
    """
    Download a file with progress tracking.
    
    Args:
        url: File URL
        file_path: Local file path to save
        headers: Optional headers
        chunk_size: Download chunk size
        progress_callback: Optional callback for progress updates
        
    Returns:
        bool: True if download successful
        
    Example:
        def progress(downloaded, total):
            print(f"Downloaded {downloaded}/{total} bytes")
            
        success = await download_file(
            "https://example.com/file.zip",
            "/path/to/save/file.zip",
            progress_callback=progress
        )
    """
    try:
        async with managed_http_client(headers=headers) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total_size)
                
                return True
                
    except Exception as e:
        logger.error(f"Failed to download file {url}: {e}")
        return False


# Export main functions
__all__ = [
    "create_jarvis_http_client",
    "managed_http_client", 
    "make_request_with_retry",
    "make_weather_request",
    "make_news_request",
    "make_api_request",
    "get_auth_headers",
    "get_api_key_headers",
    "download_file",
    "HttpError",
    "RateLimiter",
    "DEFAULT_TIMEOUT",
    "DEFAULT_HEADERS"
]