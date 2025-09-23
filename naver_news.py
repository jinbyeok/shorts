import requests
import json
from urllib.parse import quote

# Naver API credentials
client_id = "PfOq_XUpa6o6XyJFQSY0"
client_secret = "Fo4F512zsb"

# API URL
url = "https://openapi.naver.com/v1/search/news.json"

# Search parameters
query = "뉴스"
display = 10
start = 1
sort = "date"  # Sort by date for the latest news

# Construct the full URL with query parameters
# The requests library can handle URL encoding, but for clarity, we can build it manually too.
# query_str = f"?query={quote(query)}&display={display}&start={start}&sort={sort}"
# full_url = url + query_str

# Set up headers
headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret,
}

# Set up parameters
params = {
    "query": query,
    "display": display,
    "start": start,
    "sort": sort,
}

try:
    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        news_data = response.json()

        print("Naver 최신 뉴스 Top 10 (날짜순)\n")

        # Check if there are items in the response
        if 'items' in news_data and news_data['items']:
            for i, item in enumerate(news_data['items']):
                # Clean up the title and description by removing HTML tags
                title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&amp;', '&')
                description = item['description'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&amp;', '&')

                print(f"[{i+1}] {title}")
                print(f"  - 링크: {item['link']}")
                print(f"  - 요약: {description}\n")
        else:
            print("뉴스를 찾을 수 없습니다.")

    else:
        # Print error details if the request failed
        print(f"Error: {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
