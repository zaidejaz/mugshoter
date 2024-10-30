class ScrapingTarget:
    def __init__(self, state: str, county: str, url: str):
        self.state = state
        self.county = county
        self.url = url

    def __str__(self):
        return f"ScrapingTarget(state={self.state}, county={self.county}, url={self.url})"