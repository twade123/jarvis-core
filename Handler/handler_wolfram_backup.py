"""
Handler for Wolfram Alpha computational knowledge engine queries.

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

import sys
from pathlib import Path
import urllib.request

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

# Dynamically add the Wolfram directory to sys.path
current_dir = Path(__file__).resolve().parent
wolfram_dir = current_dir.parent / "Wolfram"
sys.path.append(str(wolfram_dir))

# Now import the package
from Python_Binding_1_1 import wap


# Load API Key
API_KEY_FILE = current_dir.parent / "API" / "WOLFRAM_API_KEY.txt"  # Corrected path resolution
if not API_KEY_FILE.exists():
    raise FileNotFoundError(f"Wolfram API Key file not found. Please ensure the file exists at '{API_KEY_FILE}'.")

with open(API_KEY_FILE, "r") as f:
    WOLFRAM_API_KEY = f.read().strip()

# Wolfram|Alpha API Server
WOLFRAM_SERVER = "https://api.wolframalpha.com/v2/query"

# Initialize WolframAlpha Engine
wa_engine = wap.WolframAlphaEngine(WOLFRAM_API_KEY, WOLFRAM_SERVER)

def query_wolfram_alpha(query):
    """
    Perform a query to Wolfram|Alpha and return results.
    Args:
        query (str): The input query string.
    Returns:
        dict: Processed results, including plaintext and images.
    """
    try:
        # Create query string
        query_str = wa_engine.CreateQuery(query)
        
        # Perform query
        response = wa_engine.PerformQuery(query_str)
        
        # Parse response
        result = wap.WolframAlphaQueryResult(response)
        
        # Extract pods and results
        parsed_results = {}
        for pod in result.Pods():
            wa_pod = wap.Pod(pod)
            pod_title = wa_pod.Title()[0]
            pod_results = []
            
            for subpod in wa_pod.Subpods():
                wa_subpod = wap.Subpod(subpod)
                plaintext = wa_subpod.Plaintext()[0] if wa_subpod.Plaintext() else None
                img = wa_subpod.Img()
                img_src = wap.scanbranches(img[0], "src")[0] if img else None
                pod_results.append({"plaintext": plaintext, "img_src": img_src})
            
            parsed_results[pod_title] = pod_results
        
        return parsed_results
    
    except Exception as e:
        print(f"Error querying Wolfram|Alpha: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    sample_query = input("Enter your Wolfram|Alpha query: ")
    results = query_wolfram_alpha(sample_query)
    
    if results:
        print("\nWolfram|Alpha Results:")
        for pod_title, pod_content in results.items():
            print(f"\nPod: {pod_title}")
            for content in pod_content:
                print(f"  Text: {content.get('plaintext')}")
                print(f"  Image: {content.get('img_src')}")
    else:
        print("No results found.")