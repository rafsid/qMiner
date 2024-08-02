from bs4 import BeautifulSoup
import requests

url = "https://www.walmart.com/ip/Lenovo-IdeaCentre-3i-27-inch-FHD-IPS-Touch-All-in-One-Desktop-Intel-Core-i5-12450H-8GB-RAM-512GB-SSD-Black/2183074919?adsRedirect=true"

response = requests.get(url)

HEADERS = {
    
    "Accept": "*/*", 
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
}


soup = BeautifulSoup(response.text, "html.parser")

script_tag = soup.find("script", id="__NEXT_DATA__")
html = script_tag.string

print(html)
