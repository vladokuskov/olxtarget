import requests
from helpers.helpers import fetch_data


async def fetch_olx_products(product_name: str, limit = 10):
    url = "https://www.olx.ua/api/v1/offers/"

    params = {
        "offset": 0,
        "limit": limit,
        "query": product_name,
        "currency": "UAH",
        "sort_by": "created_at:desc",
        "filter_refiners": "spell_checker",
        "suggest_filters": "true",
    }

    try:
        data = fetch_data(url, params)
        products = data.get('data', [])

        return products
    except requests.RequestException:
        return []



