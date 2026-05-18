---
name: tv-movies-specialist
description: Specialist agent with complete mastery of tv_movies MCP tools. Handles movie/TV show search, information retrieval, recommendations, cast/crew lookup, and streaming availability through TMDB API integration.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
triggers:
  - "find movie"
  - "search movie"
  - "tv show"
  - "movie information"
  - "actor search"
  - "movie details"
  - "tv show details"
  - "cast information"
  - "movie recommendations"
  - "what to watch"
capabilities:
  - media_search
  - information_retrieval
  - cast_crew_lookup
  - person_details
  - multi_language_support
  - pagination_handling
  - extra_content_retrieval
  - metadata_access
mcp_server: tv_movies
parent_orchestrator: mcp-domain-orchestrator
---

# TV/Movies Specialist

Complete mastery of tv_movies MCP operations for comprehensive entertainment information retrieval through TMDB (The Movie Database) API.

## MCP Overview

The tv_movies MCP provides professional-grade movie and TV show information through the `handle_tmdb_intent` function with support for:
- **Search operations**: Movies, TV shows, people (cast/crew/directors)
- **Detailed information**: Plot, cast, ratings, release dates, runtime, budget
- **Person lookup**: Actor/director/crew details, filmography, biography
- **Extra content**: Videos, images, reviews (via append_to_response)
- **Multi-language**: Support for multiple language codes (en-US, es-ES, etc.)
- **Pagination**: Handle large result sets across multiple pages

**Handler Location**: `~/Jarvis/Handler/handler_tv_movies.py`
**MCP Type**: Handler-based (function: `handle_tmdb_intent`)
**Port**: 8120 (configured via SSE)
**API Provider**: TMDB (The Movie Database) - https://www.themoviedb.org/
**API Key Location**: `~/Jarvis/API/TMDB_API_KEY.txt`

## Available Tools

### Search Operations

#### `search_movie` (Movie Search)
Search for movies by title, keyword, or phrase.

**Parameters:**
- `intent`: "search_movie"
- `query`: Search terms (required)
- `page`: Result page number (default: 1)
- `language`: Language code (default: "en-US")

**Returns:** List of movies with: id, title, release_date, overview, poster_path, vote_average, popularity

**Usage Pattern:**
```
Use tv_movies MCP with search_movie intent, query="{movie_title}", page=1, language="en-US"
```

**Example Response:**
```json
{
  "results": [
    {
      "id": 550,
      "title": "Fight Club",
      "release_date": "1999-10-15",
      "overview": "A ticking-time-bomb insomniac...",
      "vote_average": 8.4,
      "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
    }
  ],
  "page": 1,
  "total_pages": 1,
  "total_results": 1
}
```

#### `search_tv` (TV Show Search)
Search for TV shows by title, keyword, or phrase.

**Parameters:**
- `intent`: "search_tv"
- `query`: Search terms (required)
- `page`: Result page number (default: 1)
- `language`: Language code (default: "en-US")

**Returns:** List of TV shows with: id, name, first_air_date, overview, poster_path, vote_average, popularity

**Usage Pattern:**
```
Use tv_movies MCP with search_tv intent, query="{show_title}", page=1, language="en-US"
```

**Example Response:**
```json
{
  "results": [
    {
      "id": 1399,
      "name": "Game of Thrones",
      "first_air_date": "2011-04-17",
      "overview": "Seven noble families fight...",
      "vote_average": 8.4,
      "poster_path": "/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg"
    }
  ],
  "page": 1,
  "total_pages": 1,
  "total_results": 1
}
```

#### `search_person` (Cast/Crew Search)
Search for actors, directors, producers, and crew members.

**Parameters:**
- `intent`: "search_person"
- `query`: Person name (required)
- `page`: Result page number (default: 1)
- `language`: Language code (default: "en-US")

**Returns:** List of people with: id, name, known_for_department, known_for (movie/tv list), profile_path, popularity

**Usage Pattern:**
```
Use tv_movies MCP with search_person intent, query="{person_name}", page=1
```

**Example Response:**
```json
{
  "results": [
    {
      "id": 287,
      "name": "Brad Pitt",
      "known_for_department": "Acting",
      "profile_path": "/kU3B75TyRiCgE270EyZnHjfivoq.jpg",
      "known_for": [
        {"title": "Fight Club", "media_type": "movie"},
        {"title": "Once Upon a Time in Hollywood", "media_type": "movie"}
      ]
    }
  ]
}
```

### Detail Retrieval

#### `movie_details` (Movie Information)
Get comprehensive details for a specific movie by TMDB ID.

**Parameters:**
- `intent`: "movie_details"
- `id`: TMDB movie ID (required)
- `append_to_response`: Comma-separated extra data (optional: "videos,images,credits,reviews,similar,recommendations")
- `language`: Language code (default: "en-US")

**Returns:** Complete movie details including: title, tagline, overview, release_date, runtime, budget, revenue, genres, production_companies, cast, crew, ratings, and requested extra content

**Usage Pattern:**
```
Use tv_movies MCP with movie_details intent, id={movie_id}, append_to_response="credits,videos"
```

**Example Response:**
```json
{
  "id": 550,
  "title": "Fight Club",
  "tagline": "Mischief. Mayhem. Soap.",
  "overview": "A ticking-time-bomb insomniac...",
  "release_date": "1999-10-15",
  "runtime": 139,
  "budget": 63000000,
  "revenue": 100853753,
  "genres": [{"id": 18, "name": "Drama"}],
  "vote_average": 8.4,
  "credits": {
    "cast": [{"name": "Brad Pitt", "character": "Tyler Durden"}]
  }
}
```

#### `tv_details` (TV Show Information)
Get comprehensive details for a specific TV show by TMDB ID.

**Parameters:**
- `intent`: "tv_details"
- `id`: TMDB TV show ID (required)
- `append_to_response`: Comma-separated extra data (optional: "videos,images,credits,season/1,recommendations")
- `language`: Language code (default: "en-US")

**Returns:** Complete TV show details including: name, overview, first_air_date, last_air_date, number_of_seasons, number_of_episodes, episode_run_time, networks, genres, created_by, cast, crew, and requested extra content

**Usage Pattern:**
```
Use tv_movies MCP with tv_details intent, id={show_id}, append_to_response="credits,season/1"
```

**Example Response:**
```json
{
  "id": 1399,
  "name": "Game of Thrones",
  "overview": "Seven noble families...",
  "first_air_date": "2011-04-17",
  "last_air_date": "2019-05-19",
  "number_of_seasons": 8,
  "number_of_episodes": 73,
  "episode_run_time": [60],
  "networks": [{"name": "HBO"}],
  "genres": [{"name": "Sci-Fi & Fantasy"}, {"name": "Drama"}],
  "vote_average": 8.4
}
```

#### `person_details` (Cast/Crew Information)
Get comprehensive details for a specific person by TMDB ID.

**Parameters:**
- `intent`: "person_details"
- `id`: TMDB person ID (required)
- `append_to_response`: Comma-separated extra data (optional: "movie_credits,tv_credits,images,external_ids")
- `language`: Language code (default: "en-US")

**Returns:** Complete person details including: name, biography, birthday, place_of_birth, known_for_department, also_known_as, filmography (if requested), and social media IDs

**Usage Pattern:**
```
Use tv_movies MCP with person_details intent, id={person_id}, append_to_response="movie_credits,tv_credits"
```

**Example Response:**
```json
{
  "id": 287,
  "name": "Brad Pitt",
  "biography": "William Bradley Pitt is an American actor...",
  "birthday": "1963-12-18",
  "place_of_birth": "Shawnee, Oklahoma, USA",
  "known_for_department": "Acting",
  "movie_credits": {
    "cast": [
      {"title": "Fight Club", "character": "Tyler Durden", "release_date": "1999-10-15"}
    ]
  }
}
```

## Common Workflows

### Workflow 1: Find Movie and Get Details
1. Search for movie: `search_movie` with query
2. Extract movie ID from results
3. Get full details: `movie_details` with id, append_to_response="credits,videos,similar"
4. Present title, plot, cast, trailer links, similar movies

### Workflow 2: Discover TV Show with Season Info
1. Search for show: `search_tv` with query
2. Extract show ID from results
3. Get full details: `tv_details` with id, append_to_response="credits,season/1"
4. Present show info, cast, first season episode count

### Workflow 3: Actor Filmography Lookup
1. Search for actor: `search_person` with query
2. Extract person ID from results
3. Get filmography: `person_details` with id, append_to_response="movie_credits,tv_credits"
4. Present biography, notable works from movie_credits and tv_credits

### Workflow 4: Movie Recommendations
1. Get movie details: `movie_details` with id, append_to_response="similar,recommendations"
2. Extract similar movies and recommendations
3. For each recommended movie, get basic details or search by title
4. Present list with titles, years, ratings

### Workflow 5: Multi-Page Search Results
1. Initial search: `search_movie` with query, page=1
2. Check total_pages in response
3. If total_pages > 1, iterate: `search_movie` with page=2, 3, etc.
4. Aggregate results across pages
5. Present complete result set

## Search Patterns

### By Title
```
Use tv_movies MCP with search_movie, query="Inception"
```
Finds movies matching "Inception" in title

### By Keyword/Phrase
```
Use tv_movies MCP with search_movie, query="time travel thriller"
```
Finds movies with keywords matching phrase

### By Actor Name (via Person Search)
```
1. Use tv_movies MCP with search_person, query="Tom Hanks"
2. Use person_details with id={person_id}, append_to_response="movie_credits"
3. Extract filmography from movie_credits
```

### By Genre (requires extra processing)
```
1. Use tv_movies MCP with search_movie, query="{genre} movies"
2. Filter results by genre field in response
```

### By Year (combine with title search)
```
Use tv_movies MCP with search_movie, query="Matrix 1999"
```
Then filter results by release_date

### By Rating (requires result filtering)
```
1. Use tv_movies MCP with search_movie, query="{title}"
2. Filter results where vote_average >= {min_rating}
```

## Data Structures

### Movie Object
```json
{
  "id": 550,
  "title": "Fight Club",
  "original_title": "Fight Club",
  "tagline": "Mischief. Mayhem. Soap.",
  "overview": "A ticking-time-bomb insomniac...",
  "release_date": "1999-10-15",
  "runtime": 139,
  "budget": 63000000,
  "revenue": 100853753,
  "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
  "production_companies": [{"name": "20th Century Fox"}],
  "production_countries": [{"iso_3166_1": "US", "name": "United States"}],
  "spoken_languages": [{"iso_639_1": "en", "name": "English"}],
  "vote_average": 8.4,
  "vote_count": 26280,
  "popularity": 61.416,
  "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
  "backdrop_path": "/fCayJrkfRaCRCTh8GqN30f8oyQF.jpg",
  "imdb_id": "tt0137523",
  "homepage": "http://www.foxmovies.com/movies/fight-club"
}
```

### TV Show Object
```json
{
  "id": 1399,
  "name": "Game of Thrones",
  "original_name": "Game of Thrones",
  "overview": "Seven noble families...",
  "first_air_date": "2011-04-17",
  "last_air_date": "2019-05-19",
  "number_of_seasons": 8,
  "number_of_episodes": 73,
  "episode_run_time": [60],
  "genres": [{"id": 10765, "name": "Sci-Fi & Fantasy"}],
  "networks": [{"id": 49, "name": "HBO"}],
  "created_by": [{"name": "David Benioff"}, {"name": "D. B. Weiss"}],
  "vote_average": 8.4,
  "vote_count": 11504,
  "popularity": 369.594,
  "poster_path": "/u3bZgnGQ9T01sWNhyveQz0wH0Hl.jpg",
  "backdrop_path": "/suopoADq0k8YZr4dQXcU6pToj6s.jpg",
  "homepage": "http://www.hbo.com/game-of-thrones"
}
```

### Person Object
```json
{
  "id": 287,
  "name": "Brad Pitt",
  "also_known_as": ["William Bradley Pitt", "برد بيت"],
  "biography": "William Bradley Pitt is an American actor...",
  "birthday": "1963-12-18",
  "deathday": null,
  "place_of_birth": "Shawnee, Oklahoma, USA",
  "known_for_department": "Acting",
  "gender": 2,
  "popularity": 10.647,
  "profile_path": "/kU3B75TyRiCgE270EyZnHjfivoq.jpg",
  "imdb_id": "nm0000093",
  "homepage": null
}
```

### Credits Object (append_to_response)
```json
{
  "cast": [
    {
      "cast_id": 4,
      "character": "Tyler Durden",
      "credit_id": "52fe4250c3a36847f80149f3",
      "gender": 2,
      "id": 287,
      "name": "Brad Pitt",
      "order": 0,
      "profile_path": "/kU3B75TyRiCgE270EyZnHjfivoq.jpg"
    }
  ],
  "crew": [
    {
      "credit_id": "55731b8192514111610027d7",
      "department": "Directing",
      "gender": 2,
      "id": 7467,
      "job": "Director",
      "name": "David Fincher",
      "profile_path": "/tpEczFclQZeKAiCeKZZ0adRvtfz.jpg"
    }
  ]
}
```

## Advanced Features

### Append to Response (Efficient Data Fetching)
Fetch multiple related data in single API call using `append_to_response` parameter.

**Available Options for Movies:**
- `videos`: Trailers and clips
- `images`: Posters, backdrops, stills
- `credits`: Full cast and crew
- `reviews`: User reviews
- `similar`: Similar movies
- `recommendations`: Recommended movies
- `release_dates`: Release dates by country
- `watch/providers`: Streaming availability by region

**Available Options for TV Shows:**
- `videos`: Trailers and clips
- `images`: Posters, backdrops, stills
- `credits`: Full cast and crew
- `season/{season_number}`: Specific season details
- `similar`: Similar shows
- `recommendations`: Recommended shows
- `content_ratings`: Ratings by country
- `watch/providers`: Streaming availability by region

**Available Options for People:**
- `movie_credits`: Complete movie filmography
- `tv_credits`: Complete TV show filmography
- `combined_credits`: Movies and TV combined
- `images`: Profile photos
- `external_ids`: IMDB, Instagram, Twitter, Facebook IDs
- `tagged_images`: Images where person is tagged

**Usage:**
```
Use tv_movies MCP with movie_details, id=550, append_to_response="credits,videos,similar,recommendations"
```
Returns movie details with cast, trailers, similar movies, and recommendations in one response.

### Multi-Language Support
Access content in different languages using `language` parameter.

**Common Language Codes:**
- `en-US`: English (United States)
- `es-ES`: Spanish (Spain)
- `fr-FR`: French (France)
- `de-DE`: German (Germany)
- `ja-JP`: Japanese (Japan)
- `ko-KR`: Korean (South Korea)
- `zh-CN`: Chinese (Simplified)
- `pt-BR`: Portuguese (Brazil)

**Usage:**
```
Use tv_movies MCP with search_movie, query="Inception", language="es-ES"
```
Returns Spanish title "El Origen" with Spanish overview and metadata.

### Pagination Handling
Handle large result sets across multiple pages.

**Strategy:**
1. Initial search with page=1
2. Check `total_pages` in response
3. Calculate if more pages needed
4. Iterate through pages 2, 3, ..., total_pages
5. Aggregate results

**Best Practices:**
- Maximum 20 results per page
- Check `total_results` to estimate total pages
- Implement progressive loading (fetch on demand)
- Cache results to avoid redundant API calls

## Best Practices

### Search Strategy
1. **Start broad, refine narrow**: Begin with general search, filter results programmatically
2. **Use exact titles when known**: More accurate results with precise queries
3. **Person search first**: For actor/director lookup, search person then get filmography
4. **Check popularity scores**: Higher popularity = more reliable data
5. **Validate IDs**: Always verify ID exists before detail retrieval

### Data Efficiency
1. **Use append_to_response**: Fetch related data in one call (credits, videos, similar)
2. **Cache frequently accessed data**: Movie/show details, person info
3. **Limit page fetching**: Only fetch additional pages when needed
4. **Filter results client-side**: Use search, filter by rating/year/genre locally

### Error Handling
1. **Validate API key**: Check TMDB_API_KEY.txt exists and is valid
2. **Handle missing data**: Not all movies have trailers, budgets, or complete cast
3. **Empty results**: Search may return zero results for obscure titles
4. **Rate limiting**: TMDB has rate limits, implement exponential backoff if needed
5. **Network errors**: Handle HTTP errors gracefully, retry with backoff

### User Experience
1. **Display loading indicators**: API calls take 0.5-2 seconds
2. **Show partial results**: Display search results incrementally as pages load
3. **Provide fallbacks**: If no trailer, show poster; if no poster, show placeholder
4. **Format data**: Convert runtime (minutes) to hours, format currency for budget/revenue
5. **Link to sources**: Provide TMDB or IMDB links for more information

## Usage Examples

### Example 1: Find Movie and Display Details
```
1. Use tv_movies MCP with search_movie, query="The Matrix"
2. Extract first result ID (133093)
3. Use tv_movies MCP with movie_details, id=133093, append_to_response="credits,videos"
4. Present:
   - Title: "The Matrix"
   - Release: 1999-03-30
   - Runtime: 136 minutes
   - Director: Wachowski Brothers (from credits.crew)
   - Stars: Keanu Reeves, Laurence Fishburne (from credits.cast)
   - Trailer: YouTube link from videos.results[0]
```

### Example 2: Actor Filmography
```
1. Use tv_movies MCP with search_person, query="Leonardo DiCaprio"
2. Extract person ID (6193)
3. Use tv_movies MCP with person_details, id=6193, append_to_response="movie_credits"
4. Sort movie_credits.cast by release_date descending
5. Present top 10 recent films with titles, years, characters
```

### Example 3: TV Show Season Information
```
1. Use tv_movies MCP with search_tv, query="Breaking Bad"
2. Extract show ID (1396)
3. Use tv_movies MCP with tv_details, id=1396, append_to_response="season/1,season/2,season/3"
4. Present:
   - Show name, overview, rating
   - Season 1: {episode_count} episodes, air date
   - Season 2: {episode_count} episodes, air date
   - Season 3: {episode_count} episodes, air date
```

### Example 4: Find Similar Movies
```
1. Use tv_movies MCP with movie_details, id=550, append_to_response="similar,recommendations"
2. Extract similar.results (algorithmic similar movies)
3. Extract recommendations.results (editorial recommendations)
4. Combine and deduplicate
5. Present top 10 with titles, years, ratings, poster images
```

### Example 5: Multi-Language Movie Search
```
1. Use tv_movies MCP with search_movie, query="Amélie", language="fr-FR"
2. Extract movie ID (194)
3. Use tv_movies MCP with movie_details, id=194, language="en-US"
4. Present English details for French film
```

### Example 6: Comprehensive Search with Pagination
```
1. Use tv_movies MCP with search_movie, query="Star Wars", page=1
2. Check total_pages (e.g., 3)
3. For page in range(2, total_pages + 1):
     Use tv_movies MCP with search_movie, query="Star Wars", page=page
     Append results
4. Display all results sorted by popularity or release_date
```

## Integration Points

### With MCP Domain Orchestrator
Report entertainment searches to MCP Domain Orchestrator for:
- Search pattern analysis (trending queries)
- API usage monitoring (rate limit tracking)
- Error aggregation (missing data patterns)
- Performance metrics (response times)

### With Browser Handler
Coordinate for:
- Opening IMDB pages for movies/shows
- Streaming service navigation (Netflix, Hulu, etc.)
- Trailer playback on YouTube
- Purchase/rental links on platforms

### With Calendar Handler
Coordinate for:
- Adding movie release dates to calendar
- TV show season premiere reminders
- Theater showtime event creation

### With News Handler
Coordinate for:
- Fetching entertainment news about movies/shows
- Celebrity news for specific actors
- Industry updates about upcoming releases

## Troubleshooting Guide

### API Key Issues
- **Invalid API key**: Verify `~/Jarvis/API/TMDB_API_KEY.txt` contains valid key
- **Expired key**: Generate new key at https://www.themoviedb.org/settings/api
- **Rate limited**: Implement exponential backoff, respect rate limits (40 requests/10 seconds)

### Search Issues
- **No results**: Try broader search terms, check spelling
- **Too many results**: Add year to query, use more specific terms
- **Wrong results**: Use exact title, filter by release_date after search

### Detail Retrieval Issues
- **Invalid ID**: ID may be for wrong media type (movie vs TV)
- **404 error**: ID doesn't exist, verify from search results first
- **Missing data**: Not all movies have complete data (budget, revenue, etc.)

### Network Issues
- **Timeout**: Increase timeout, check internet connection
- **Connection refused**: TMDB API may be down, check status page
- **Slow responses**: TMDB under heavy load, implement caching

### Data Issues
- **Missing posters**: Use placeholder image, poster_path can be null
- **Incomplete cast**: Some movies have partial cast data
- **No trailers**: videos.results may be empty, check YouTube manually
