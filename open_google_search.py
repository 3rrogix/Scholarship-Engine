from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse

city = "Gilroy"
state = "California"
search_terms = "computer science scholarships"

# Combine search terms with city and state
query = f"{search_terms} {city} {state}"
encoded_query = urllib.parse.quote_plus(query)
url = f"https://www.google.com/search?q={encoded_query}"

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)
input('Google search should be open. Press Enter to close...')
driver.quit()
