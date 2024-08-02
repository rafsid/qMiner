import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import requests
from bs4 import BeautifulSoup
import pandas as pd
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image
import io
import langchain
import langchain_community
from langchain_community.llms import OpenAI

# Ensure you have Tesseract OCR installed and its path set correctly
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print('Restarting script...')
            projects = scrape_html(url)
            pdf_text = extract_pdf_text(pdf_url)
            image_text = extract_image_text(image_url)
            all_text = '\n\n'.join([project['Description'] for project in projects]) + '\n\n' + pdf_text + '\n\n' + image_text
            summary = summarize_text(all_text)
            print(summary)

def scrape_html(url):
    """
    Function to scrape HTML content from a website.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    projects = []
    # Adjust based on the specific structure of the website
    for project in soup.find_all('div', class_='project-item'):
        title = project.find('h2').text
        description = project.find('p', class_='description').text
        deadline = project.find('span', class_='deadline').text
        projects.append({'Title': title, 'Description': description, 'Deadline': deadline})
    return projects

def extract_pdf_text(url):
    """
    Function to extract text from a PDF file.
    """
    response = requests.get(url)
    pdf = PdfReader(io.BytesIO(response.content))
    text = ""
    for page in pdf.pages:
        text += page.extract_text()
    return text

def extract_image_text(url):
    """
    Function to extract text from an image using OCR.
    """
    response = requests.get(url)
    img = Image.open(io.BytesIO(response.content))
    text = pytesseract.image_to_string(img)
    return text

def summarize_text(text):
    """
    Function to summarize text using LLM.
    """
    prompt = f"Summarize the following text: {text}"
    llm = OpenAI(api_key='your_openai_api_key')
    summary = llm.generate(prompt)
    return summary



if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()