#!/usr/bin/env python3
"""
Fixed Handler for Wolfram Alpha computational knowledge engine queries.

This version bypasses the buggy wap library and uses direct HTTP requests
with proper XML parsing for better reliability.

Capabilities:
    - Mathematical computations
    - Scientific calculations
    - Data analysis
    - Knowledge-based queries
    - Image result handling
    - Pod-based information
    - Multi-format responses
    - Technical computations
    - Natural language processing
    - Educational content
    - Research assistance
    - Data visualization

Patterns:
    - "calculate {expression}"
    - "solve {equation}"
    - "analyze {data}"
    - "convert {units}"
    - "compare {items}"
    - "find {information}"
    - "plot {function}"
    - "explain {concept}"

Intents:
    - wolfram_calculate
    - wolfram_solve
    - wolfram_analyze
    - wolfram_convert
    - wolfram_compare
    - wolfram_find
    - wolfram_plot
    - wolfram_explain

Parameters:
    - query: string (input query)
    - format: string (response format)
    - include_pods: List[string]
    - exclude_pods: List[string]
    - max_width: integer
    - plot_width: integer
    - timeout: integer
"""

import urllib.request
import urllib.parse
from xml.dom import minidom
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API Key
current_dir = Path(__file__).resolve().parent
API_KEY_FILE = current_dir.parent / "API" / "WOLFRAM_API_KEY.txt"

if not API_KEY_FILE.exists():
    raise FileNotFoundError(f"Wolfram API Key file not found. Please ensure the file exists at '{API_KEY_FILE}'.")

with open(API_KEY_FILE, "r") as f:
    WOLFRAM_API_KEY = f.read().strip()

# Wolfram|Alpha API Server (HTTPS)
WOLFRAM_SERVER = "https://api.wolframalpha.com/v2/query"

class WolframHandler:
    """Enhanced Wolfram Alpha handler with better error handling and reliability."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or WOLFRAM_API_KEY
        self.base_url = WOLFRAM_SERVER
        
    def query_wolfram_alpha(self, query, format_type='plaintext', include_pods=None, 
                          exclude_pods=None, timeout=30, max_width=500):
        """
        Perform a query to Wolfram|Alpha and return results.
        
        Args:
            query (str): The input query string
            format_type (str): Response format ('plaintext', 'image', 'mathml')
            include_pods (List[str]): Specific pods to include
            exclude_pods (List[str]): Specific pods to exclude
            timeout (int): Request timeout in seconds
            max_width (int): Maximum width for images
            
        Returns:
            dict: Processed results, including plaintext and images
        """
        try:
            # Construct parameters
            params = {
                'input': query,
                'appid': self.api_key,
                'format': format_type
            }
            
            # Add optional parameters
            if include_pods:
                params['includepodid'] = ','.join(include_pods)
            if exclude_pods:
                params['excludepodid'] = ','.join(exclude_pods)
            if max_width:
                params['width'] = str(max_width)
                
            # Construct URL
            query_string = urllib.parse.urlencode(params)
            full_url = f"{self.base_url}?{query_string}"
            
            logger.debug(f"Querying Wolfram Alpha: {query}")
            
            # Make request
            request = urllib.request.Request(full_url)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = response.read().decode('utf-8')
                
            # Parse XML response
            parsed_results = self._parse_wolfram_response(result)
            
            logger.info(f"Successfully processed query: '{query}' - {len(parsed_results)} pods")
            return parsed_results
            
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error querying Wolfram Alpha: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"URL error querying Wolfram Alpha: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Error querying Wolfram Alpha: {str(e)}")
            return None
    
    def _parse_wolfram_response(self, xml_response):
        """
        Parse the XML response from Wolfram Alpha.
        
        Args:
            xml_response (str): Raw XML response
            
        Returns:
            dict: Parsed results organized by pod
        """
        try:
            # Parse XML
            dom = minidom.parseString(xml_response)
            
            # Check if query was successful
            queryresult = dom.getElementsByTagName('queryresult')[0]
            success = queryresult.getAttribute('success')
            error = queryresult.getAttribute('error')
            
            if success != 'true':
                logger.warning(f"Wolfram query not successful: success={success}, error={error}")
                return {}
            
            # Extract pods
            parsed_results = {}
            pods = dom.getElementsByTagName('pod')
            
            for pod in pods:
                pod_title = pod.getAttribute('title')
                pod_id = pod.getAttribute('id')
                pod_results = []
                
                # Extract subpods
                subpods = pod.getElementsByTagName('subpod')
                for subpod in subpods:
                    subpod_data = {}
                    
                    # Extract plaintext
                    plaintext_nodes = subpod.getElementsByTagName('plaintext')
                    if plaintext_nodes and plaintext_nodes[0].firstChild:
                        subpod_data['plaintext'] = plaintext_nodes[0].firstChild.nodeValue
                    
                    # Extract images
                    img_nodes = subpod.getElementsByTagName('img')
                    if img_nodes:
                        img_data = {
                            'src': img_nodes[0].getAttribute('src'),
                            'alt': img_nodes[0].getAttribute('alt'),
                            'title': img_nodes[0].getAttribute('title'),
                            'width': img_nodes[0].getAttribute('width'),
                            'height': img_nodes[0].getAttribute('height')
                        }
                        subpod_data['img'] = img_data
                    
                    # Extract MathML if present
                    mathml_nodes = subpod.getElementsByTagName('mathml')
                    if mathml_nodes:
                        subpod_data['mathml'] = mathml_nodes[0].toxml()
                    
                    pod_results.append(subpod_data)
                
                parsed_results[pod_title] = {
                    'id': pod_id,
                    'subpods': pod_results
                }
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"Error parsing Wolfram response: {str(e)}")
            return {}
    
    def get_pod_titles(self, query):
        """Get just the pod titles for a query (useful for debugging)."""
        results = self.query_wolfram_alpha(query)
        if results:
            return list(results.keys())
        return []
    
    def get_simple_answer(self, query):
        """Get just the simple answer for a query."""
        results = self.query_wolfram_alpha(query)
        if results:
            # Look for Result pod first
            if 'Result' in results:
                subpods = results['Result']['subpods']
                if subpods and 'plaintext' in subpods[0]:
                    return subpods[0]['plaintext']
            
            # Fall back to first pod with plaintext
            for pod_title, pod_data in results.items():
                if pod_data['subpods']:
                    first_subpod = pod_data['subpods'][0]
                    if 'plaintext' in first_subpod:
                        return first_subpod['plaintext']
        
        return None

# Create global handler instance
wolfram_handler = WolframHandler()

# Maintain backward compatibility with original function name
def query_wolfram_alpha(query, **kwargs):
    """
    Backward compatibility function for existing code.
    
    Args:
        query (str): The input query string
        **kwargs: Additional parameters
        
    Returns:
        dict: Processed results in the original format
    """
    results = wolfram_handler.query_wolfram_alpha(query, **kwargs)
    
    if not results:
        return None
    
    # Convert to original format for backward compatibility
    converted_results = {}
    for pod_title, pod_data in results.items():
        pod_results = []
        for subpod in pod_data['subpods']:
            converted_subpod = {
                'plaintext': subpod.get('plaintext'),
                'img_src': subpod.get('img', {}).get('src')
            }
            pod_results.append(converted_subpod)
        converted_results[pod_title] = pod_results
    
    return converted_results

# MCP Server Integration
class WolframMCPHandler:
    """MCP-compatible handler for Wolfram Alpha queries."""
    
    def __init__(self):
        self.handler = WolframHandler()
        self.name = "wolfram"
        self.description = "Wolfram Alpha computational knowledge engine"
        
    async def handle_query(self, query: str, **kwargs) -> dict:
        """Handle a query request via MCP."""
        try:
            result = self.handler.query_wolfram_alpha(query, **kwargs)
            return {
                'status': 'success',
                'data': result,
                'query': query
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'query': query
            }
    
    def get_capabilities(self) -> dict:
        """Return handler capabilities for MCP registration."""
        return {
            'name': self.name,
            'description': self.description,
            'methods': [
                'query_wolfram_alpha',
                'get_simple_answer',
                'get_pod_titles'
            ],
            'parameters': {
                'query': {'type': 'string', 'required': True},
                'format_type': {'type': 'string', 'default': 'plaintext'},
                'include_pods': {'type': 'list', 'default': None},
                'exclude_pods': {'type': 'list', 'default': None},
                'timeout': {'type': 'integer', 'default': 30},
                'max_width': {'type': 'integer', 'default': 500}
            }
        }

if __name__ == "__main__":
    # Test the handler
    test_queries = [
        "2 + 2",
        "solve x^2 - 4 = 0",
        "derivative of sin(x)",
        "population of New York City",
        "convert 100 miles to kilometers"
    ]
    
    for query in test_queries:
        print(f"\nTesting: {query}")
        result = query_wolfram_alpha(query)
        if result:
            print(f"✓ Success - {len(result)} pods")
            for pod_title, pod_content in list(result.items())[:2]:  # First 2 pods
                print(f"  {pod_title}:")
                for subpod in pod_content[:1]:  # First subpod
                    if subpod.get('plaintext'):
                        print(f"    {subpod['plaintext']}")
        else:
            print("✗ Failed")