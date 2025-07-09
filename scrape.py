import json
import time
import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
import pytesseract
from PIL import Image
import io
from langchain_community.llms import OpenAI

# Tesseract OCR setup
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FileModificationHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            logging.info('Restarting script... Current working directory: %s', os.getcwd())
            try:
                html_content = """<your provided HTML snippet here>"""
                scraped_content = scrape_html(html_content)
                save_to_file(json.dumps(scraped_content, indent=4), 'scraped_content.json')
            except Exception as e:
                logging.error(f"Error during processing: {e}")

def scrape_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        content = {'Main Title': soup.find('h1').text.strip() if soup.find('h1') else ''}
        
        for section in soup.find_all('section'):
            section_title_tag = section.find('h2')
            if section_title_tag:
                section_title = section_title_tag.text.strip()
                section_content = section.text.replace(section_title, '').strip()
                content[section_title] = section_content
        
        return content
    except Exception as e:
        logging.error(f"Error scraping HTML: {e}")
        return {}

def extract_text_from_url(url, extractor_func):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return extractor_func(io.BytesIO(response.content))
    except requests.RequestException as e:
        logging.error(f"Error downloading content: {e}")
        return ""
    except Exception as e:
        logging.error(f"Error extracting text: {e}")
        return ""

def extract_pdf_text(file):
    try:
        pdf = PdfReader(file)
        return " ".join(page.extract_text() for page in pdf.pages)
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_image_text(file):
    try:
        img = Image.open(file)
        return pytesseract.image_to_string(img)
    except Exception as e:
        logging.error(f"Error extracting text from image: {e}")
        return ""

OPENROUTER_API_KEY = "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"

def summarize_text(text, api_key):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = json.dumps({
            "model": "deepseek/deepseek-chat",
            "messages": [
                { "role": "user", "content": f"Summarize the following text: {text}" }
            ]
        })
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get("choices")[0].get("message").get("content")
        else:
            logging.error(f"Error summarizing text: {response.status_code} - {response.text}")
            return "Summary could not be generated."
    except Exception as e:
        logging.error(f"Error summarizing text: {e}")
        return "Summary could not be generated."

def save_to_file(content, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        logging.info(f"Content saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving content to file: {e}")

if __name__ == "__main__":
    logging.info("Starting script... Current working directory: %s", os.getcwd())
    event_handler = FileModificationHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping script...")
    finally:
        observer.stop()
        observer.join()
