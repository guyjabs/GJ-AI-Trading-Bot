from openai import OpenAI
import re
import json
import os
from config import OPENAI_MODEL_NAME
from src.utils import logger
from src.utils.retry import retry_with_backoff


# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


# Make AI request to OpenAI API
@retry_with_backoff(retries=3, backoff_in_seconds=2)
def make_ai_request(messages, model=OPENAI_MODEL_NAME, response_format=None):
    """
    Send a request to OpenAI API with retries.
    Args:
        messages (str or list): The prompt string or list of message dicts.
        model (str): Model name.
        response_format (dict): Optional JSON schema.
    """
    try:
        # Backward compatibility: Wrap string prompt
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        kwargs = {
            "model": model,
            "messages": messages
        }
        if response_format:
            kwargs["response_format"] = response_format

        ai_resp = client.chat.completions.create(**kwargs)
        return ai_resp
    except Exception as e:
        # Log the error and re-raise to be caught by the retry mechanism
        logger.error(f"OpenAI API request failed: {e}")
        raise


# Parse AI response
def parse_ai_response(ai_response, return_raw=False):
    content = ai_response.choices[0].message.content.strip()
    try:
        # Try to find JSON block (object or array)
        json_match = re.search(r'```json\s*(.*?)```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            decisions = json.loads(json_str)
        else:
            # Fallback: try to find just the array or object
            # Look for [...] or {...}
            bracket_match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
            if bracket_match:
                json_str = bracket_match.group(1).strip()
                decisions = json.loads(json_str)
            else:
                 # Last resort: try to parse the whole content if it's just JSON
                decisions = json.loads(content)
                
    except (json.JSONDecodeError, AttributeError) as e:
        # Log the raw content for debugging
        print(f"Failed to parse AI response. Raw content: {content}")
        raise Exception(f"Invalid JSON response from OpenAI: {e}")
    
    if return_raw:
        return decisions, content
        
    return decisions
