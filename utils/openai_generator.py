from openai import OpenAI

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OpenAIGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)


    def generate_content(self, prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 200) -> str:
        try:
            response = self.client.chat.completions.create(model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating content with OpenAI: {e}")
            return ""

    def generate_from_template(self, template: str, data: Dict[str, Any]) -> str:
        try:
            prompt = template.format(**data)
            return self.generate_content(prompt)
        except KeyError as e:
            logger.error(f"Missing key in data for template: {e}")
            return ""
        except Exception as e:
            logger.error(f"Error generating content from template: {e}")
            return ""
