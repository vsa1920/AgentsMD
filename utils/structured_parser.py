from pydantic import BaseModel
from openai import OpenAI
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_structured_output(
    text,
    schema_model,
    system_prompt = "Extract the relevant information from the text.",
    model = "gpt-4o-2024-08-06"
):
    """
    Parse text input using GPT-4 to extract structured information based on a Pydantic model.
    
    Args:
        text (str): The input text to parse
        schema_model (Type[T]): The Pydantic model class defining the structure
        system_prompt (str): Custom system prompt for the model
        model (str): The OpenAI model to use
        
    Returns:
        T: An instance of the provided Pydantic model with extracted information
        
    Example:
        class Person(BaseModel):
            name: str
            age: int
            
        text = "John is 25 years old"
        result = parse_structured_output(text, Person)
    """
    
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format=schema_model,
    )
    
    return json.loads(completion.choices[0].message.parsed.model_dump_json())
