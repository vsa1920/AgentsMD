import os
import json
import time
import requests
from openai import OpenAI

def query_model(model_str, system_prompt, prompt, openai_api_key=None, max_retries=3, retry_delay=2):
    """
    Query a language model with the given prompts
    
    Args:
        model_str (str): Model identifier
        system_prompt (str): System prompt
        prompt (str): User prompt
        openai_api_key (str, optional): API key
        max_retries (int): Maximum number of retries on failure
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        str: Model response
    """
    # Use environment variable if no API key provided
    if not openai_api_key:
        openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Map model string to actual model names if needed
    model_mapping = {
        "o1-mini": "o1-mini",
        "o1-preview": "o1-preview",
        "o1": "o1",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini"
    }
    
    # Use the mapped model name if available, otherwise use the provided model string
    model_name = model_mapping.get(model_str, model_str)
    
    return query_openai(model_name, system_prompt, prompt, openai_api_key, max_retries, retry_delay)

def query_openai(model_str, system_prompt, prompt, api_key=None, max_retries=3, retry_delay=2):
    """Query OpenAI models"""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
    
    for attempt in range(max_retries):
        try:
            client = OpenAI(api_key=api_key)
            
            # For o1 models, we need to use a different format and parameters
            if model_str.startswith("o1"):
                response = client.chat.completions.create(
                    model=model_str,
                    messages=[
                        {"role": "user", "content": f"{system_prompt}\n\n{prompt}"}
                    ],
                    max_completion_tokens=4000  # Use max_completion_tokens instead of max_tokens
                    # No temperature parameter for o1 models - they only support the default
                )
            else:
                response = client.chat.completions.create(
                    model=model_str,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
            
            return response.choices[0].message.content
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error querying OpenAI model: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to query OpenAI model after {max_retries} attempts: {e}")