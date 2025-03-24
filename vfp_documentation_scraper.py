import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re
from urllib.parse import urljoin, urlparse

class VFPDocScraper:
    def __init__(self, index_url, output_file):
        self.index_url = index_url
        self.output_file = output_file
        self.visited_urls = set()
        self.results = []
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def fetch_page(self, url):
        """Fetch a page and return the BeautifulSoup object"""
        try:
            print(f"Fetching: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_keyword_content(self, url):
        """Extract content from a keyword page"""
        soup = self.fetch_page(url)
        if not soup:
            return None
            
        # Extract title
        title = soup.title.text.strip() if soup.title else "No title"
        
        # Extract main content (assuming main content is in the body)
        main_content = soup.body
        if not main_content:
            return {
                'url': url,
                'title': title,
                'text_content': [],
                'code_blocks': []
            }
        
        # Extract text content (paragraphs, headings, list items)
        text_content = []
        for element in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
            # Exclude navigation elements if possible
            if element.parent and element.parent.name in ['nav', 'header', 'footer']:
                continue
                
            text = element.get_text(strip=True)
            if text:
                text_content.append(text)
        
        # Extract code blocks
        code_blocks = []
        for code in main_content.find_all(['pre', 'code']):
            code_text = code.get_text(strip=True)
            if code_text:
                code_blocks.append(code_text)
        
        return {
            'url': url,
            'title': title,
            'text_content': text_content,
            'code_blocks': code_blocks
        }
    
    def scrape_alphabet_index(self):
        """Scrape the main alphabetical index page"""
        print(f"Scraping alphabetical index at {self.index_url}")
        
        # Fetch the index page
        soup = self.fetch_page(self.index_url)
        if not soup:
            print("Failed to fetch the index page. Exiting.")
            return
        
        # Find all letter links (A-Z and @)
        letter_links = []
        
        # Look for links that likely represent alphabet indexes
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            link_text = a_tag.get_text(strip=True)
            
            # Check if the link text is a single letter or '@'
            if (len(link_text) == 1 and link_text.isalpha()) or link_text == '@':
                if 'section4/' in href or href.startswith('#'):
                    full_url = urljoin(self.index_url, href)
                    letter_links.append((link_text, full_url))
        
        print(f"Found {len(letter_links)} letter index links")
        
        # Process each letter page
        for letter, letter_url in letter_links:
            self.scrape_letter_page(letter, letter_url)
            
            # Be nice to the server
            time.sleep(1)
    
    def scrape_letter_page(self, letter, url):
        """Scrape a letter index page for keyword links"""
        print(f"Scraping '{letter}' index at {url}")
        
        # Fetch the letter page
        soup = self.fetch_page(url)
        if not soup:
            print(f"Failed to fetch the letter page for '{letter}'. Skipping.")
            return
        
        # Find all keyword links
        keyword_links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Skip non-section4 links or already processed ones
            if 'section4/' not in href:
                continue
                
            full_url = urljoin(url, href)
            
            # Skip if we've already visited this URL
            parsed = urlparse(full_url)
            normalized_url = f"{parsed.netloc}{parsed.path}"
            
            if normalized_url in self.visited_urls:
                continue
                
            self.visited_urls.add(normalized_url)
            keyword_links.append((a_tag.get_text(strip=True), full_url))
        
        print(f"Found {len(keyword_links)} keyword links for '{letter}'")
        
        # Process each keyword page
        for keyword, keyword_url in keyword_links:
            print(f"Processing keyword: {keyword}")
            keyword_data = self.extract_keyword_content(keyword_url)
            
            if keyword_data:
                self.results.append(keyword_data)
            
            # Be nice to the server
            time.sleep(1)
    
    def save_results(self):
        """Save the scraped data to a JSON file"""
        print(f"Saving {len(self.results)} keyword pages to {self.output_file}")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'base_url': self.index_url,
                'total_keywords': len(self.results),
                'scraped_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': self.results
            }, f, indent=2)
        
        print(f"Data successfully saved to {self.output_file}")
    
    def run(self):
        """Run the complete scraping process"""
        print(f"Starting to scrape VFP documentation from {self.index_url}")
        self.scrape_alphabet_index()
        self.save_results()
        print(f"Scraping complete. Scraped {len(self.results)} keyword pages.")


if __name__ == "__main__":
    # Configuration
    index_url = 'https://hackfox.github.io/section4/'
    output_file = 'vfp_keywords_documentation.json'
    
    # Run the scraper
    scraper = VFPDocScraper(index_url, output_file)
    scraper.run()