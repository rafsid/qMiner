import json
import time
import logging
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            logging.info('Restarting script...')
            try:
                url = 'http://example.com'  # Define your URL here
                pdf_url = 'http://example.com/document.pdf'  # Define your PDF URL here
                image_url = 'http://example.com/image.jpg'  # Define your image URL here
                html_content = """<your provided HTML snippet here>"""
                scraped_content = scrape_html(html_content)
                save_to_file(json.dumps(scraped_content, indent=4), 'scraped_content.json')
                logging.info("Scraped content saved to scraped_content.json")
            except Exception as e:
                logging.error(f"Error during processing: {e}")

def scrape_html(html_content):
    """
    Function to scrape HTML content from a provided HTML snippet.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        content = {}
        
        # Extract the main title
        main_title_tag = soup.find('h1')
        if main_title_tag:
            content['Main Title'] = main_title_tag.text.strip()
        
        # Extract sections with class 'section'
        sections = soup.find_all('section')
        for section in sections:
            section_title_tag = section.find('h2')
            if section_title_tag:
                section_title = section_title_tag.text.strip()
                section_content = section.text.replace(section_title, '').strip()
                content[section_title] = section_content
        
        return content
    except Exception as e:
        logging.error(f"Error scraping HTML: {e}")
        return {}

def extract_pdf_text(url):
    """
    Function to extract text from a PDF file.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        pdf = PdfReader(io.BytesIO(response.content))
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text
    except requests.RequestException as e:
        logging.error(f"Error downloading PDF: {e}")
        return ""
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_image_text(url):
    """
    Function to extract text from an image using OCR.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        text = pytesseract.image_to_string(img)
        return text
    except requests.RequestException as e:
        logging.error(f"Error downloading image: {e}")
        return ""
    except Exception as e:
        logging.error(f"Error extracting text from image: {e}")
        return ""

def summarize_text(text):
    """
    Function to summarize text using LLM.
    """
    try:
        prompt = f"Summarize the following text: {text}"
        llm = OpenAI(api_key='your_openai_api_key')
        summary = llm.generate(prompt)
        return summary
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        return "Summary could not be generated."

def save_to_file(content, filename):
    """
    Function to save content to a local file.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        logging.info(f"Content saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving content to file: {e}")

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
    logging.info("Starting script...")
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping script...")
        observer.stop()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    observer.join()
