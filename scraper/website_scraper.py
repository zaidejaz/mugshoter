import time
import random
import requests
from requests.exceptions import RequestException
from fake_useragent import UserAgent
import logging
from bs4 import BeautifulSoup
import io
from datetime import datetime, timedelta
from scraper.database import DatabaseManager
from scraper.s3_uploader import SupabaseUploader
from utils.image_processor import ImageProcessor
from config import BASE_URL, STATE, COUNTY

class WebsiteScraper:
    def __init__(self, logger):
        self.logger = logger
        self.user_agent = UserAgent()
        self.session = self._create_session()
        self.base_url = BASE_URL
        self.state = STATE
        self.county = COUNTY
        self.running = True
        self.last_scrape_date = None
        self.request_count = 0
        self.session_start_time = time.time()

    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.user_agent.random,
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        return session

    def _rotate_session(self):
        self.session = self._create_session()
        self.request_count = 0
        self.session_start_time = time.time()
        self.logger.info("Rotated to a new session with a new User-Agent.")

    def _make_request(self, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                if self.request_count >= 100 or time.time() - self.session_start_time > 3600:
                    self._rotate_session()
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                self.request_count += 1
                
                wait_time = random.uniform(2, 5) * (2 ** attempt)
                time.sleep(wait_time)
                
                return response
            except RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to access {url} after {max_retries} attempts. Rotating session...")
                    self._rotate_session()
                    time.sleep(random.uniform(60, 120))
                    raise
                time.sleep(random.uniform(10, 20))

    def scrape(self):
        while self.running:
            try:
                self.scrape_current_month()
                self.logger.info("Sleeping for 5 minutes before next scrape...")
                for _ in range(30):
                    if not self.running:
                        break
                    time.sleep(10)
            except Exception as e:
                self.logger.error(f"Error in main scraping loop: {str(e)}")
                self.logger.exception("Exception details:")
                time.sleep(60)

    def scrape_current_month(self):
        current_date = datetime.now().date()
        current_year, current_month = current_date.year, current_date.month
        url = f"{self.base_url}/{current_year}/{current_month:02d}/"
        page = 1

        while self.running:
            try:
                page_url = url if page == 1 else f"{url}page/{page}/"
                self.logger.info(f"Scraping {page_url}")
                response = self._make_request(page_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                articles = soup.find_all('h2', class_='entry-title')
                if not articles:
                    self.logger.info("No more articles found. Ending scrape.")
                    break
                
                self.logger.info(f"Found {len(articles)} articles on page {page}")
                
                new_mugshots_found = False
                for article in articles:
                    if not self.running:
                        break
                    
                    link = article.find('a')['href']
                    article_text = article.get_text(strip=True)
                    try:
                        name_parts = article_text.split()
                        date_str = name_parts[-1]
                        firstName = name_parts[0].replace("'", "")
                        lastName = " ".join(name_parts[1:-1]).replace("'", "")
                        booking_date = datetime.strptime(date_str, "%m/%d/%Y").date()

                        if booking_date > current_date:
                            self.logger.warning(f"Found future date {booking_date}, skipping")
                            continue
                        
                        if booking_date < current_date:
                            self.logger.info(f"Found mugshot from {booking_date}, stopping scrape.")
                            return

                        if not DatabaseManager.is_in_database(firstName, lastName, booking_date):
                            self.process_article(link)
                            new_mugshots_found = True
                        else:
                            self.logger.info(f"Mugshot already in database: {firstName} {lastName}")
                    except Exception as e:
                        self.logger.error(f"Error processing article title: {article_text} - {str(e)}")
                        continue                
                if not new_mugshots_found:
                    self.logger.info("No new mugshots found on this page. Stopping scrape.")
                    return
                
                page += 1
            except Exception as e:
                self.logger.error(f"Error scraping {page_url}: {str(e)}")
                self.logger.exception("Exception details:")
                break

    def get_booking_date(self, title):
        try:
            date_str = title.split()[-1]
            return datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            self.logger.error(f"Could not parse date from title: {title}")
            return datetime.now().date()

    def process_article(self, url):
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find('h1').text.strip()
            name_parts = title.split()
            date_str = name_parts[-1]
            firstName = name_parts[0]
            lastName = " ".join(name_parts[1:-1])
            booking_date = datetime.strptime(date_str, "%m/%d/%Y").date()
            
            self.scrape_mugshot(url, soup, firstName, lastName, booking_date, date_str)
        except Exception as e:
            self.logger.error(f"Error processing article {url}: {str(e)}")
            self.logger.exception("Exception details:")

    def scrape_mugshot(self, url, soup, firstName, lastName, booking_date, date_str):
        try:
            img_tag = soup.find('img', class_='attachment-full')
            image_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None
            
            details_div = soup.find('div', class_='entry-content')
            details_html = details_div.prettify() if details_div else ""
            
            offense_description, additional_details = DatabaseManager.parse_content(details_html)
            
            if image_url:
                image_response = self._make_request(image_url)
                image_data = image_response.content
                
                image_file = io.BytesIO(image_data)
                cropped_image = ImageProcessor.crop_image(image_file)
                
                filename = SupabaseUploader.generate_filename(firstName, lastName, date_str)
                supabase_url = SupabaseUploader.upload_to_supabase(cropped_image, filename)
                
                if supabase_url:
                    mugshot_data = {
                        "firstName": firstName,
                        "lastName": lastName,
                        "dateOfBooking": booking_date,
                        "stateOfBooking": self.state,
                        "countyOfBooking": self.county,
                        "offenseDescription": offense_description,
                        "additionalDetails": additional_details, 
                        "imagePath": supabase_url,
                        "fb_status": "pending"
                    }
                    DatabaseManager.insert_mugshot(mugshot_data)
                    self.logger.info(f"Successfully processed: {firstName} {lastName} {booking_date}")
                else:
                    self.logger.warning(f"Failed to upload image for: {firstName} {lastName}")
            else:
                self.logger.warning(f"No image found for: {firstName} {lastName}")
        except Exception as e:
            self.logger.error(f"Error processing mugshot from {url}: {str(e)}")
            self.logger.exception("Exception details:")

    def stop(self):
        self.running = False
        self.logger.info("Stopping scraper...")