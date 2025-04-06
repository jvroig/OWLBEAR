import os
import requests
import json

def brave_web_search(query, count=10):
    """
    Search the web using Brave Search API.
    
    Args:
        query (str): The search query.
        count (int, optional): The number of results to return. Defaults to 10.
        
    Returns:
        dict: A dictionary containing the search results or an error message.
    """
    try:
        # Get API key from environment variables
        api_key = os.environ.get('BRAVE_API_KEY')
        if not api_key:
            return {"error": "BRAVE_API_KEY environment variable not found"}
        
        # Prepare the API request
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        params = {
            "q": query,
            "count": count
        }
        
        # Make the API request
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Return the JSON response
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Failed to decode JSON response"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}