import os
from datetime import datetime

def generate_quick_reference(case_id, esi_level, confidence, actions, chief_complaint=None, output_dir="quick_ref"):
    """
    Generate a quick reference file for nurses
    
    Args:
        case_id (str): The case ID
        esi_level (str): The ESI level (1-5)
        confidence (int): Confidence level (0-100)
        actions (list): List of recommended actions
        chief_complaint (str, optional): Chief complaint
        output_dir (str): Directory to save the output file
        
    Returns:
        str: Path to the generated file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Format the quick reference
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create a more subtle header
    output = f"""# Emergency Triage - Quick Reference

**Case ID:** {case_id}  
**Generated:** {timestamp}

## ESI LEVEL: {esi_level}
**Confidence:** {confidence}%

"""
    
    # Add chief complaint if available
    if chief_complaint:
        output += f"**Chief Complaint:** {chief_complaint}\n\n"
    
    # Add recommended actions
    output += "## Recommended Actions:\n\n"
    for i, action in enumerate(actions, 1):
        output += f"{i}. {action}\n"
    
    # Add ESI level descriptions for reference
    output += """
## ESI Level Reference:
- **Level 1:** Requires immediate life-saving intervention
- **Level 2:** High risk situation; severe pain/distress
- **Level 3:** Requires multiple resources but stable vital signs
- **Level 4:** Requires one resource
- **Level 5:** Requires no resources
"""
    
    # Save to file
    filename = f"{output_dir}/{case_id}_quick_ref_{timestamp}.txt"
    with open(filename, "w") as f:
        f.write(output)
    
    return filename