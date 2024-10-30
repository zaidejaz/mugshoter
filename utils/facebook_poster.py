import requests
import logging

class FacebookPoster:
    def __init__(self, access_token, page_id, logger):
        self.access_token = access_token
        self.page_id = page_id
        self.graph_api_url = f'https://graph.facebook.com/{page_id}/photos'
        self.logger = logger

    def post_to_facebook(self, message, image_url):
        params = {
            'message': message,
            'access_token': self.access_token,
            'url': image_url,
        }

        try:
            response = requests.post(self.graph_api_url, params=params)
            response.raise_for_status()
            self.logger.info("Post successful!")
            self.logger.info(response.json())
            return True
        except requests.RequestException as e:
            self.logger.error(f"Error posting to Facebook: {e}")
            if response:
                self.logger.error(f"Response status code: {response.status_code}")
                self.logger.error(f"Response content: {response.text}")
            return False