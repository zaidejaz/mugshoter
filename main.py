import logging
from logging.handlers import TimedRotatingFileHandler
import multiprocessing
import time
import signal
import os
from scraper.database import DatabaseManager
from config import FACEBOOK_ACCESS_TOKEN, FACEBOOK_PAGE_ID, OPENAI_KEY
import gunicorn.app.base
from datetime import date
from flask import Flask, render_template_string, Response
import queue

# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = 'mugshot_scraper.log'
file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=3)
file_handler.setFormatter(log_formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

# Create a queue for storing log messages
log_queue = multiprocessing.Queue()

# Custom handler to capture logs for web display
class QueueHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        log_queue.put(log_entry)

queue_handler = QueueHandler()
queue_handler.setFormatter(log_formatter)

# Create a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)
logger.addHandler(queue_handler)

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mugshot Scraper Logs</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            #log-container { height: 80vh; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; }
            .log { margin-bottom: 10px; }
        </style>
        <script>
            var eventSource = new EventSource("/stream");
            eventSource.onmessage = function(e) {
                var logContainer = document.getElementById('log-container');
                logContainer.innerHTML += '<div class="log">' + e.data + '</div>';
                logContainer.scrollTop = logContainer.scrollHeight;
            };
        </script>
    </head>
    <body>
        <h1>Mugshot Scraper Logs</h1>
        <div id="log-container"></div>
    </body>
    </html>
    '''
    return render_template_string(html_template)

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            try:
                message = log_queue.get(timeout=1)
                yield f"data: {message}\n\n"
            except queue.Empty:
                yield f"data: Checking\n\n"
            time.sleep(0.1)
    return Response(event_stream(), content_type='text/event-stream')

class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def run_web_server():
    options = {
        'bind': '0.0.0.0:5000',
        'workers': 1,
        'timeout': 120,
    }
    StandaloneApplication(app, options).run()

def scrape_data(exit_event):
    from scraper.website_scraper import WebsiteScraper
    scraper = WebsiteScraper(logger)
    while not exit_event.is_set():
        try:
            logger.info("Starting scraping process")
            scraper.scrape()
            logger.info("Scraping process completed")
            for _ in range(60):  # 5 minutes in 5-second increments
                if exit_event.is_set():
                    break
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            logger.exception("Exception details:")
    logger.info("Scraper process shutting down")

def process_data_and_post_to_facebook(exit_event):
    from utils.facebook_poster import FacebookPoster
    from utils.openai_generator import OpenAIGenerator
    from utils.prompt import get_prompt

    fb_poster = FacebookPoster(FACEBOOK_ACCESS_TOKEN, FACEBOOK_PAGE_ID, logger)
    ai_generator = OpenAIGenerator(OPENAI_KEY)

    while not exit_event.is_set():
        try:
            today = date.today()
            new_records = DatabaseManager.get_todays_unprocessed_mugshots(today)
            
            if not new_records:
                logger.info("No new records found for today. Waiting for new data...")
                time.sleep(60)
                continue

            for record in new_records:
                if exit_event.is_set():
                    break
                try:
                    if record.dateOfBooking != today:
                        logger.warning(f"Skipping record {record.id} as it's not from today.")
                        continue

                    prompt = get_prompt(record)
                    generated_content = ai_generator.generate_content(prompt)
                    logger.info("Generated content successfully.")

                    post_success = fb_poster.post_to_facebook(generated_content, record.imagePath)

                    if post_success:
                        DatabaseManager.mark_as_processed(record.id)
                        logger.info(f"Record {record.id} processed and posted successfully.")
                    else:
                        logger.error(f"Failed to post record {record.id} to Facebook. Not marking as processed.")

                    time.sleep(18)  # Respect Facebook's rate limit

                except Exception as e:
                    logger.error(f"Error processing record {record.id}: {str(e)}")
                    logger.exception("Exception details:")
        except Exception as e:
            logger.error(f"Error in process_data_and_post_to_facebook: {str(e)}")
            logger.exception("Exception details:")
    logger.info("Facebook posting process shutting down")

def signal_handler(signum, frame):
    logger.info("Received shutdown signal. Stopping all processes...")
    exit_event.set()

if __name__ == "__main__":
    # Check if start method is already set
    if multiprocessing.get_start_method(allow_none=True) is None:
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            logger.warning("Could not set start method to 'spawn'. Using default method.")
    
    exit_event = multiprocessing.Event()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        DatabaseManager.create_table_if_not_exists()
        logger.info("Initialized components successfully.")
        
        scrape_process = multiprocessing.Process(target=scrape_data, args=(exit_event,))
        post_process = multiprocessing.Process(target=process_data_and_post_to_facebook, args=(exit_event,))
        web_process = multiprocessing.Process(target=run_web_server)

        scrape_process.start()
        post_process.start()
        web_process.start()

        # Wait for processes to complete
        scrape_process.join()
        post_process.join()
        web_process.join()

    except Exception as e:
        logger.error(f"An error occurred in the main function: {e}")
        logger.exception("Exception details:")
    finally:
        exit_event.set()
        for process in [scrape_process, post_process, web_process]:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        logger.error("All processes terminated.")