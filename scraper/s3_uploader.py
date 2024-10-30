import logging
import io
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET_NAME

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class SupabaseUploader:
    @staticmethod
    def upload_to_supabase(image_data: io.BytesIO, filename: str) -> str:
        try:
            logger.info(f"Checking if image already exists in Supabase: {filename}")
            
            # Check if the file already exists
            existing_files = supabase.storage.from_(SUPABASE_BUCKET_NAME).list(path=filename)
            if any(file['name'] == filename for file in existing_files):
                url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(filename)
                logger.info(f"Image already exists in Supabase: {url}")
                return url

            logger.info(f"Uploading new image to Supabase: {filename}")
            
            # Reset the file pointer to the beginning of the file
            image_data.seek(0)
            
            # Read the content of the BytesIO object
            file_contents = image_data.read()
            
            # Upload the file to Supabase storage
            result = supabase.storage.from_(SUPABASE_BUCKET_NAME).upload(
                path=filename,
                file=file_contents,
                file_options={"content-type": "image/jpeg"}
            )
            
            logger.info(f"Upload result: {result}")
            
            # Check if the upload was successful
            if hasattr(result, 'status_code') and result.status_code == 200:
                # Generate the public URL for the uploaded file
                url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(filename)
                logger.info(f"Successfully uploaded image to Supabase: {url}")
                return url
            elif isinstance(result, dict) and 'path' in result:
                # If result is a dictionary with 'path', assume it's successful
                url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(result['path'])
                logger.info(f"Successfully uploaded image to Supabase: {url}")
                return url
            else:
                logger.error(f"Failed to upload. Unexpected result: {result}")
                return ""

        except Exception as e:
            if "The resource already exists" in str(e):
                logger.info(f"Image already exists in Supabase: {filename}")
                url = supabase.storage.from_(SUPABASE_BUCKET_NAME).get_public_url(filename)
                return url
            else:
                logger.error(f"Failed to upload to Supabase: {str(e)}")
                logger.exception("Exception details:")
                return ""

    @staticmethod
    def generate_filename(first_name: str, last_name: str, date_str: str) -> str:
        safe_first_name = ''.join(c for c in first_name if c.isalnum())
        safe_last_name = ''.join(c for c in last_name if c.isalnum())
        safe_date = date_str.replace('/', '-')
        return f"{safe_first_name}_{safe_last_name}_{safe_date}.jpg"