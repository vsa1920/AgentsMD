import os
import json
from datetime import datetime
from utils.query_model import query_model

def generate_differential_diagnoses(case_id, assessment_results, output_dir="differential_diagnoses"):
    """
    Generate potential differential diagnoses based on assessment results
    
    Args:
        case_id (str): The case ID
        assessment_results (dict): The assessment results
        output_dir (str): Directory to save the output file
        
    Returns:
        str: Path to the generated file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the API key from the environment
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # Create a prompt for generating differential diagnoses
    prompt = f"""
    Based on the following patient assessment, generate a list of potential differential diagnoses.
    For each diagnosis, provide:
    1. The diagnosis name
    2. Key supporting findings from the case
    3. Additional tests that would help confirm or rule out this diagnosis
    
    ASSESSMENT RESULTS:
    ESI Level: {assessment_results.get('esi_level')}
    Justification: {assessment_results.get('justification')}
    Recommended Actions: {', '.join(assessment_results.get('recommended_actions', []))}
    Discussion Summary: {assessment_results.get('discussion_summary')}
    
    Format your response as a structured list of differential diagnoses, from most to least likely.
    """
    
    # System prompt for the model
    system_prompt = """
    You are an expert emergency medicine physician with extensive diagnostic experience.
    Your task is to generate a comprehensive differential diagnosis list based on the patient information provided.
    Focus on the most likely diagnoses first, but include important "must-not-miss" diagnoses even if they are less likely.
    For each diagnosis, provide specific supporting evidence from the case and suggest targeted diagnostic tests.
    Be specific and concise in your explanations.
    """
    
    # Generate the differential diagnoses using the model
    model_response = query_model(
        model_str="o1-mini",  # Use o1-mini for consistency
        system_prompt=system_prompt,
        prompt=prompt,
        openai_api_key=api_key
    )
    
    # Format the output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = f"""
DIFFERENTIAL DIAGNOSES
=====================
Case ID: {case_id}
Generated: {timestamp}

{model_response}
"""
    
    # Save to file
    filename = f"{output_dir}/{case_id}_differential_diagnoses_{timestamp}.txt"
    with open(filename, "w") as f:
        f.write(output)
    
    return filename 