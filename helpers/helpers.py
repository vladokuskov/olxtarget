from typing import Dict, Any
import requests
from helpers.logger import logger


def fetch_data(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data from the given URL with the provided parameters.

    Args:
        url (str): The URL to fetch data from.
        params (Dict[str, Any]): The query parameters for the request.

    Returns:
        Dict[str, Any]: The JSON response from the server.

    Raises:
        requests.RequestException: If the request fails.
    """
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch data: {e}")
        raise