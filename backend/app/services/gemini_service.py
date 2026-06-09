import re
import logging
import google.generativeai as genai
from backend.app.config import settings

logger = logging.getLogger("app.gemini_service")

class GeminiService:
    def __init__(self):
        self._configured = False

    def _configure(self):
        if not self._configured:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                logger.warning("GEMINI_API_KEY environment variable is not set. Gemini API calls will fail.")
            else:
                genai.configure(api_key=api_key)
                self._configured = True

    def generate_shorts_metadata(self, filename: str) -> dict:
        """Generates viral title, description, and hashtags for a football clip filename."""
        self._configure()
        
        prompt = f"""
Clip filename:
{filename}

You are a football YouTube Shorts growth expert.
Given the football clip filename, generate:
1. A viral YouTube Shorts title (under 70 characters)
2. A YouTube description (2-3 lines)
3. 15-20 high-performing football hashtags

Rules:
- Title must be under 70 characters
- Title must have high CTR, emotional hooks, and be curiosity driven
- Include player names if detected
- Include tournament names if detected

Mandatory hashtags:
#football #soccer #footballshorts #shorts #fyp #fifa #fifaworldcup #worldcup #wc26

Output exactly this structure:
TITLE:
[Title text here]

DESCRIPTION:
[Description text here]

HASHTAGS:
[Space-separated hashtags here]
"""
        logger.info(f"Generating metadata for file: {filename}")
        
        try:
            # We use gemini-2.5-flash as specified in the original activepieces flow or gemini-1.5-flash/gemini-2.5-flash
            # Let's use gemini-1.5-flash or gemini-2.5-flash (gemini-1.5-flash has wider availability and is extremely reliable)
            # We can try gemini-2.5-flash and fallback to gemini-1.5-flash if needed.
            model_name = "gemini-2.5-flash"
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text
            logger.debug(f"Gemini raw response:\n{text}")
            
            # Parse response
            metadata = self._parse_response(text)
            return metadata
        except Exception as e:
            logger.error(f"Error generating content from Gemini: {e}")
            raise e

    def _parse_response(self, text: str) -> dict:
        """Parses the structured output from Gemini response."""
        title = ""
        description = ""
        hashtags = ""

        # Using regex to extract sections
        title_match = re.search(r"TITLE:\s*(.*?)(?=\nDESCRIPTION:|\nHASHTAGS:|$)", text, re.IGNORECASE | re.DOTALL)
        desc_match = re.search(r"DESCRIPTION:\s*(.*?)(?=\nHASHTAGS:|\nTITLE:|$)", text, re.IGNORECASE | re.DOTALL)
        hash_match = re.search(r"HASHTAGS:\s*(.*)", text, re.IGNORECASE | re.DOTALL)

        if title_match:
            title = title_match.group(1).strip().strip('"').strip("'")
        if desc_match:
            description = desc_match.group(1).strip()
        if hash_match:
            hashtags = hash_match.group(1).strip()

        # Clean hashtags: make sure they are space separated
        if hashtags:
            # extract all hashtags using regex #\w+
            found_hashtags = re.findall(r"#\w+", hashtags)
            
            # Ensure mandatory hashtags are included
            mandatory = ["#football", "#soccer", "#footballshorts", "#shorts", "#fyp", "#fifa", "#fifaworldcup", "#worldcup", "#wc26"]
            for tag in mandatory:
                if tag not in found_hashtags:
                    found_hashtags.append(tag)
            
            hashtags = " ".join(found_hashtags)

        # Fallbacks if parsing fails
        if not title:
            title = "Amazing Football Moment! ⚽"
        if not description:
            description = "Check out this incredible football highlight! Subscribe for more viral football shorts."
        if not hashtags:
            hashtags = "#football #soccer #footballshorts #shorts #fyp #fifa #fifaworldcup #worldcup #wc26"

        return {
            "title": title[:70], # Ensure under 70 chars
            "description": description,
            "hashtags": hashtags
        }

gemini_service = GeminiService()
