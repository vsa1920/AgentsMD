import re
from utils.query_model import query_model
from utils.esi_examples import load_esi_examples, format_examples_for_prompt
from utils.schema import ConsultantAssessment
from utils.structured_parser import parse_structured_output

class MedicalConsultantAgent:
    def __init__(self, model="gpt-4o-mini", api_key=None):
        """
        Initialize the Medical Consultant Agent
        
        Args:
            model (str): LLM model to use
            api_key (str): API key for the LLM service
        """
        self.model = model
        self.api_key = api_key
        self.role = "Medical Consultant"
    
    def assess_conversation(self, conversation_text):
        """
        Provide specialized assessment based on the conversation
        
        Args:
            conversation_text (str): The nurse-patient conversation
            
        Returns:
            dict: Specialized assessment
        """
        # Create a system prompt for the medical consultant role
        system_prompt = self._get_system_prompt()
        
        # Create the user prompt
        user_prompt = f"""
        Please provide a specialized medical consultant assessment based on the following patient-nurse conversation:
        
        {conversation_text}
        
        Provide your assessment in the following format:
        1. Specialist Impression:
        2. Differential Considerations (including rare but critical diagnoses):
        3. ESI Level Evaluation:
        4. Specialized Recommendations (list at least 3-4 specific actions):
        5. Potential Pitfalls/Concerns:
        6. Additional Insights:
        """
        
        # Query the model
        response = query_model(
            model_str=self.model,
            system_prompt=system_prompt,
            prompt=user_prompt,
            openai_api_key=self.api_key
        )
        
        # Parse the response
        assessment = parse_structured_output(response, ConsultantAssessment)
        
        return assessment
    
    def respond_to_assessments(self, conversation_text, assessments):
        """
        Respond to other agents' assessments
        
        Args:
            conversation_text (str): The nurse-patient conversation
            assessments (dict): Assessments from all agents
            
        Returns:
            str: Response to other assessments
        """
        # Create a system prompt for the response
        system_prompt = """
        You are an experienced medical consultant with expertise in emergency medicine and critical care.
        Your task is to review the assessments from other medical professionals and provide your specialized perspective.
        You should:
        1. Identify any points you agree with
        2. Note any concerns or disagreements you have
        3. Provide additional insights from a specialist perspective
        4. Identify any missed considerations or potential pitfalls
        5. Help resolve any disagreements between the other medical professionals
        
        Be professional but direct in your assessment. Your role is to provide specialized expertise and help reach the most accurate assessment.
        """
        
        # Format the assessments for the prompt
        formatted_assessments = []
        for role, assessment in assessments.items():
            if role != self.role:  # Don't include own assessment
                formatted_assessments.append(f"{role} Assessment:")
                if isinstance(assessment, dict):
                    for key, value in assessment.items():
                        formatted_assessments.append(f"- {key}: {value}")
                else:
                    formatted_assessments.append(f"- {assessment}")
        
        formatted_assessments_text = "\n".join(formatted_assessments)
        
        # Create the user prompt
        user_prompt = f"""
        Please review the following assessments from other medical professionals regarding this patient conversation:
        
        {formatted_assessments_text}
        
        The original conversation was:
        
        {conversation_text}
        
        Provide your response to these assessments, noting agreements, disagreements, and additional insights from your perspective as a medical consultant.
        Focus particularly on resolving any disagreements and identifying any missed considerations.
        """
        
        # Query the model
        response = query_model(
            model_str=self.model,
            system_prompt=system_prompt,
            prompt=user_prompt,
            openai_api_key=self.api_key
        )
        
        return response
    
    def _parse_assessment(self, response):
        """Parse the LLM response into a structured assessment"""
        assessment = {
            "specialist_impression": "",
            "differential_considerations": [],
            "esi_evaluation": "",
            "specialized_recommendations": [],
            "potential_pitfalls": "",
            "additional_insights": "",
            "summary": ""  # Add a summary field
        }
        
        # Extract sections using regex
        impression_match = re.search(r'1\.\s*Specialist Impression:(.*?)(?=2\.|\Z)', response, re.DOTALL)
        if impression_match:
            assessment["specialist_impression"] = impression_match.group(1).strip()
        
        differential_match = re.search(r'2\.\s*Differential Considerations.*?:(.*?)(?=3\.|\Z)', response, re.DOTALL)
        if differential_match:
            differential_text = differential_match.group(1).strip()
            # Extract differential diagnoses as a list
            differential_list = re.findall(r'(?:^|\n)\s*(?:-|\d+\.)\s*(.*?)(?=\n\s*(?:-|\d+\.)|\Z)', differential_text, re.DOTALL)
            assessment["differential_considerations"] = [d.strip() for d in differential_list if d.strip()]
        
        esi_match = re.search(r'3\.\s*ESI Level Evaluation:(.*?)(?=4\.|\Z)', response, re.DOTALL)
        if esi_match:
            assessment["esi_evaluation"] = esi_match.group(1).strip()
        
        recommendations_match = re.search(r'4\.\s*Specialized Recommendations:(.*?)(?=5\.|\Z)', response, re.DOTALL)
        if recommendations_match:
            recommendations_text = recommendations_match.group(1).strip()
            # Extract recommendations as a list
            recommendations_list = re.findall(r'(?:^|\n)\s*(?:-|\d+\.)\s*(.*?)(?=\n\s*(?:-|\d+\.)|\Z)', recommendations_text, re.DOTALL)
            assessment["specialized_recommendations"] = [r.strip() for r in recommendations_list if r.strip()]
        
        pitfalls_match = re.search(r'5\.\s*Potential Pitfalls/Concerns:(.*?)(?=6\.|\Z)', response, re.DOTALL)
        if pitfalls_match:
            assessment["potential_pitfalls"] = pitfalls_match.group(1).strip()
        
        insights_match = re.search(r'6\.\s*Additional Insights:(.*?)(?=\Z)', response, re.DOTALL)
        if insights_match:
            assessment["additional_insights"] = insights_match.group(1).strip()
        
        # Extract ESI level from the esi_evaluation field
        esi_digit_match = re.search(r'(\d+)', assessment["esi_evaluation"])
        esi_level = esi_digit_match.group(1) if esi_digit_match else ""
        
        # Create a summary for display in the discussion
        if esi_level:
            assessment["summary"] = f"ESI Level: {esi_level}. {assessment['specialist_impression'][:100]}..."
        else:
            assessment["summary"] = f"No clear ESI recommendation. {assessment['specialist_impression'][:100]}..."
        
        return assessment
    
    def _get_system_prompt(self):
        """Get the system prompt for the medical consultant agent"""
        # Load ESI examples - one per level
        esi_examples = load_esi_examples(num_per_level=1)
        
        # Format examples for medical consultant
        examples_text = format_examples_for_prompt(esi_examples, agent_type="consultant")
        
        base_prompt = """
        You are a senior medical consultant with expertise in emergency medicine and critical care.
        Your role is to provide specialized input on complex cases and help determine the appropriate Emergency Severity Index (ESI) level.
        
        When assessing a patient, focus on:
        1. Subtle clinical findings that might be overlooked but have significant implications
        2. Evidence-based risk factors specific to this patient's presentation
        3. Potential complications that could develop based on the specific clinical scenario
        4. Specialized resource needs with specific justification
        5. System-level considerations for optimal patient care
        
        Provide nuanced clinical insights rather than general statements. For example:
        - Instead of "patient needs monitoring" → "patient requires continuous cardiac monitoring due to concerning S1Q3T3 pattern on ECG and tachypnea, raising suspicion for pulmonary embolism despite normal oxygen saturation"
        - Instead of "patient needs specialist care" → "patient would benefit from immediate neurology consultation due to subtle right-sided facial droop and dysarthria with onset 45 minutes ago, suggesting potential eligibility for thrombolytic therapy"
        
        Your assessment should provide sophisticated clinical analysis that integrates evidence-based medicine with practical emergency department considerations.
        
        EMERGENCY SEVERITY INDEX (ESI) REFERENCE:
        - ESI Level 1: Requires immediate life-saving intervention
        - ESI Level 2: High-risk situation, severe pain/distress, or vital sign abnormalities
        - ESI Level 3: Requires multiple resources but stable vital signs
        - ESI Level 4: Requires one resource
        - ESI Level 5: Requires no resources
        
        REFERENCE EXAMPLES:
        
        {examples}
        """
        
        return base_prompt.format(examples=examples_text) 