import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

def scrape_website(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch the webpage: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    projects = []
    for project in soup.find_all('div', class_='project'):
        title_tag = project.find('h2')
        description_tag = project.find('p', class_='description')
        deadline_tag = project.find('span', class_='deadline')
        
        if title_tag and description_tag and deadline_tag:
            title = title_tag.text
            description = description_tag.text
            deadline = deadline_tag.text
            projects.append({'Title': title, 'Description': description, 'Deadline': deadline})
        else:
            logging.warning("Missing required elements in project div")
    return projects

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Scrape project data from a website.')
    parser.add_argument('url', type=str, help='The URL of the projects page')
    args = parser.parse_args()

    url = args.url
    projects = scrape_website(url)
    if projects:
        df = pd.DataFrame(projects)
        df.to_csv('projects.csv', index=False)
        logging.info("Data successfully scraped and saved to projects.csv")
    else:
        logging.info("No data scraped or saved.")
