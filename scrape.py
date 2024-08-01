import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract required data here, e.g., project titles, descriptions, deadlines
    # This will depend on the structure of the specific webpage
    projects = []
    for project in soup.find_all('div', class_='project'):
        title = project.find('h2').text
        description = project.find('p', class_='description').text
        deadline = project.find('span', class_='deadline').text
        projects.append({'Title': title, 'Description': description, 'Deadline': deadline})
    return projects

url = "https://example-organization.org/projects"
projects = scrape_website(url)
df = pd.DataFrame(projects)
df.to_csv('projects.csv', index=False)
