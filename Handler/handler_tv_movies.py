"""
Handler for TV and Movie information retrieval using TMDB API.

Capabilities:
    - Search movies and TV shows
    - Get detailed movie information
    - Get TV show details
    - Search for people/cast/crew
    - Get person details
    - Handle multiple languages
    - Pagination support
    - Extra content retrieval
    - Dynamic intent handling
    - Media metadata access

Patterns:
    - "search for movie {query}"
    - "find TV show {query}"
    - "get details for movie {id}"
    - "search for actor {query}"
    - "get TV show info {id}"
    - "find person {query}"
    - "get cast for {movie_id}"
    - "get extra content for {id}"

Intents:
    - tmdb_search_movie
    - tmdb_search_tv
    - tmdb_search_person
    - tmdb_movie_details
    - tmdb_tv_details
    - tmdb_person_details
    - tmdb_get_cast
    - tmdb_get_extras

Parameters:
    - intent: string (type of search)
    - query: string (search terms)
    - id: integer (TMDB ID)
    - append_to_response: string (extra data)
    - page: integer (result page)
    - language: string (e.g., 'en-US')
"""

import requests
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")


# Base directory for API key
BASE_DIR = Path('~/Jarvis')  # Update as needed
API_KEY_FILE = BASE_DIR / 'API/TMDB_API_KEY.txt'

def load_api_key(file_path):
    """Load the TMDB API key from environment variable or file fallback."""
    env_key = os.environ.get('TMDB_API_KEY')
    if env_key:
        return env_key
    try:
        with file_path.open('r') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Failed to load API key: {e}")
        exit()

# Load the API key
API_KEY = load_api_key(API_KEY_FILE)

BASE_URL = 'https://api.themoviedb.org/3'

def make_api_request(endpoint, params):
    """Generic function to make a TMDB API request."""
    params['api_key'] = API_KEY
    try:
        logging.info(f"Making request to {BASE_URL}{endpoint} with params {params}")
        response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logging.error(f"An error occurred: {err}")

def search_movies(query, page=1, language='en-US'):
    """Search for movies by query."""
    endpoint = '/search/movie'
    params = {'query': query, 'page': page, 'language': language}
    return make_api_request(endpoint, params)

def search_tv_shows(query, page=1, language='en-US'):
    """Search for TV shows by query."""
    endpoint = '/search/tv'
    params = {'query': query, 'page': page, 'language': language}
    return make_api_request(endpoint, params)

def search_people(query, page=1, language='en-US'):
    """Search for people by query."""
    endpoint = '/search/person'
    params = {'query': query, 'page': page, 'language': language}
    return make_api_request(endpoint, params)

def get_movie_details(movie_id, append_to_response=None, language='en-US'):
    """Get detailed information for a movie."""
    endpoint = f'/movie/{movie_id}'
    params = {'language': language}
    if append_to_response:
        params['append_to_response'] = append_to_response
    return make_api_request(endpoint, params)

def get_tv_details(tv_id, append_to_response=None, language='en-US'):
    """Get detailed information for a TV show."""
    endpoint = f'/tv/{tv_id}'
    params = {'language': language}
    if append_to_response:
        params['append_to_response'] = append_to_response
    return make_api_request(endpoint, params)

def get_person_details(person_id, append_to_response=None, language='en-US'):
    """Get detailed information for a person."""
    endpoint = f'/person/{person_id}'
    params = {'language': language}
    if append_to_response:
        params['append_to_response'] = append_to_response
    return make_api_request(endpoint, params)

def handle_tmdb_intent(intent, query=None, id=None, append_to_response=None, page=1, language='en-US'):
    """
    Handle dynamic TMDB requests based on user input.

    Args:
        intent (str): The type of search (movie, tv, person, etc.).
        query (str): The search query (for search intents).
        id (int): The TMDB ID (for detail fetch intents).
        append_to_response (str): Extra data to fetch.
        page (int): Page number for search results.
        language (str): Language for API responses.

    Returns:
        dict: The API response as a Python dictionary.
    """
    if intent == 'search_movie' and query:
        return search_movies(query, page=page, language=language)
    elif intent == 'search_tv' and query:
        return search_tv_shows(query, page=page, language=language)
    elif intent == 'search_person' and query:
        return search_people(query, page=page, language=language)
    elif intent == 'movie_details' and id:
        return get_movie_details(id, append_to_response=append_to_response, language=language)
    elif intent == 'tv_details' and id:
        return get_tv_details(id, append_to_response=append_to_response, language=language)
    elif intent == 'person_details' and id:
        return get_person_details(id, append_to_response=append_to_response, language=language)
    else:
        logging.error("Invalid intent or missing parameters.")
        return {"error": "Invalid intent or parameters"}

if __name__ == '__main__':
    # Example interactive CLI for testing
    print("Welcome to TMDB Handler!")
    intent = input("Enter intent (search_movie, search_tv, search_person, movie_details, tv_details, person_details): ").strip()
    query = input("Enter search query (if applicable): ").strip() or None
    id = input("Enter ID (if applicable): ").strip() or None
    append_to_response = input("Append extra details (e.g., videos, images)? Leave blank if none: ").strip() or None
    page = int(input("Enter page number (default is 1): ").strip() or 1)
    language = input("Enter language code (default is 'en-US'): ").strip() or 'en-US'

    if id and id.isdigit():
        id = int(id)

    result = handle_tmdb_intent(intent, query=query, id=id, append_to_response=append_to_response, page=page, language=language)

    print(json.dumps(result, indent=4))