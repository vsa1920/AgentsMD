import os
import json
import random

def load_esi_examples(num_per_level=1, seed=42):
    """
    Load ESI scenarios from JSON and select representative examples
    
    Args:
        num_per_level (int): Number of examples to select per ESI level
        seed (int): Random seed for reproducible selection
        
    Returns:
        dict: Dictionary of selected examples organized by ESI level
    """
    # Set random seed for reproducible selection
    random.seed(seed)
    
    # Load ESI scenarios from JSON
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents', 'ESI_scenarios.json')
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading ESI scenarios: {e}")
        return {}
    
    # Organize scenarios by ESI level
    scenarios_by_level = {
        "1": [],
        "2": [],
        "3": [],
        "4": [],
        "5": []
    }
    
    for scenario in data.get('scenarios', []):
        answer = scenario.get('answer', '')
        # Extract ESI level from the answer
        if 'ESI level 1' in answer:
            scenarios_by_level["1"].append(scenario)
        elif 'ESI level 2' in answer:
            scenarios_by_level["2"].append(scenario)
        elif 'ESI level 3' in answer:
            scenarios_by_level["3"].append(scenario)
        elif 'ESI level 4' in answer:
            scenarios_by_level["4"].append(scenario)
        elif 'ESI level 5' in answer:
            scenarios_by_level["5"].append(scenario)
    
    # Select examples for each level
    selected_examples = {}
    for level, scenarios in scenarios_by_level.items():
        if scenarios:
            # Select random examples up to the requested number
            selected = random.sample(scenarios, min(num_per_level, len(scenarios)))
            selected_examples[level] = selected
    
    return selected_examples

def format_examples_for_prompt(examples, agent_type="nurse"):
    """
    Format ESI examples for inclusion in agent prompts
    
    Args:
        examples (dict): Dictionary of examples organized by ESI level
        agent_type (str): Type of agent (nurse, physician, consultant)
        
    Returns:
        str: Formatted examples text
    """
    formatted_text = []
    
    for level in sorted(examples.keys()):
        for example in examples[level]:
            scenario = example.get('scenario', '')
            answer = example.get('answer', '')
            
            # Format the example based on agent type
            if agent_type == "nurse":
                formatted_text.append(f"ESI LEVEL {level} EXAMPLE:\nPatient Presentation: {scenario}\nAssessment: {answer}\n")
            elif agent_type == "physician":
                formatted_text.append(f"ESI LEVEL {level} EXAMPLE:\nClinical Scenario: {scenario}\nMedical Assessment: {answer}\n")
            elif agent_type == "consultant":
                formatted_text.append(f"ESI LEVEL {level} EXAMPLE:\nCase Presentation: {scenario}\nSpecialist Assessment: {answer}\n")
            else:
                formatted_text.append(f"ESI LEVEL {level} EXAMPLE:\nScenario: {scenario}\nAssessment: {answer}\n")
    
    return "\n".join(formatted_text) 