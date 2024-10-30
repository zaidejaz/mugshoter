# Mugshot Scraper

This application scrapes mugshot data from specified websites, processes the information, and posts it to Facebook. It includes a web interface for viewing logs in real-time.

## Features

- Web scraping of mugshot data
- Image processing and S3 upload
- Facebook posting
- Real-time log viewing through a web interface
- Dockerized deployment

## Prerequisites

- Docker
- Facebook Developer Account and App
- OpenAI API Key
- Supabase Bucket name
- Supabase API
- Supabase Postgres URL

## Important
1. Make sure that your s3 bucket is public in order to post images to facebook. 
2. Your facebook app should be live in order to view those posts as public.
3. You can extend the Facebook Token expiry using this 

- First generate token from here https://developers.facebook.com/tools/explorer/ . And then you can extend it using https://developers.facebook.com/tools/debug/accesstoken/. 

## Setup

1. Create a `.env` file in the root directory with the following content:
   ```
    DATABASE_URL=
    SUPABASE_URL=
    SUPABASE_KEY=
    SUPABASE_BUCKET_NAME=
    OPENAI_KEY=
    FACEBOOK_PAGE_ID=
    FACEBOOK_ACCESS_TOKEN=
   ```

2. Build the Docker image:
   ```
   docker build -t mugshot-scraper .
   ```

3. Run the Docker container:
   ```
   docker run --env-file .env -p 5000:5000 mugshot-scraper
   ```

## Usage

Once the container is running, you can access the log viewer by opening a web browser and navigating to `http://localhost:5000`.

The application will automatically start scraping mugshot data and posting to Facebook based on the configured intervals.

In order to add new counties. You can find scraping targets and add the State, County And Link. 

```bash
           # Define scraping targets
        targets = [
            ScrapingTarget("Texas", "Smith", "https://smithtx.mugshots.zone/"),
            ScrapingTarget("Oklahoma", "Comanche", "https://comancheok.mugshots.zone/")
        ]
        
```


## Configuration

- To add or modify scraping targets, edit the `targets` list in the `main()` function of `main.py`.

## Troubleshooting
- Ensure that your Facebook App has the necessary permissions and your access token is valid.
- Check the S3 bucket permissions if you encounter issues with image uploads.

