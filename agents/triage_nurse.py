import re
import json
import os
from utils.query_model import query_model
from utils.esi_examples import load_esi_examples, format_examples_for_prompt
from utils.schema import TriageAssessment
from utils.structured_parser import parse_structured_output

class TriageNurseAgent:
    def __init__(self, model="gpt-4o-mini", api_key=None):
        """
        Initialize the Triage Nurse Agent
        
        Args:
            model (str): LLM model to use
            api_key (str): API key for the LLM service
        """
        self.model = model
        self.api_key = api_key
        self.role = "Triage Nurse"
    
    def assess_conversation(self, conversation_text):
        """
        Perform initial assessment based on the conversation
        
        Args:
            conversation_text (str): The nurse-patient conversation
            
        Returns:
            dict: Initial assessment results
        """
        # Create a system prompt for the triage nurse role
        system_prompt = self._get_system_prompt()
        
        # Create the user prompt
        user_prompt = f"""
        Please perform an initial triage assessment based on the following patient-nurse conversation:
        
        {conversation_text}
        
        Provide your assessment in the following format:
        1. Initial Impression:
        2. Chief Complaint (as you understand it):
        3. Concerning Findings:
        4. Estimated Resource Needs:
        5. Recommended ESI Level:
        6. Rationale:
        7. Immediate Nursing Interventions (list at least 2-3 specific actions):
        8. Additional Notes:
        """
        
        # Query the model
        response = query_model(
            model_str=self.model,
            system_prompt=system_prompt,
            prompt=user_prompt,
            openai_api_key=self.api_key
        )
        
        # Parse the response
        assessment = parse_structured_output(response, TriageAssessment)
        
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
        You are an experienced emergency department triage nurse with over 15 years of experience.
        Your task is to review the assessments from other medical professionals and provide your perspective.
        You should:
        1. Identify any points you agree with
        2. Note any concerns or disagreements you have
        3. Provide additional insights from a triage nurse perspective
        4. Clarify or defend your ESI recommendation if needed
        
        Be professional but direct in your assessment. Your primary concern is patient safety and appropriate triage.
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
        
        Provide your response to these assessments, noting agreements, disagreements, and additional insights from your perspective as a triage nurse.
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
            "initial_impression": "",
            "chief_complaint": "",
            "concerning_findings": "",
            "resource_needs": "",
            "recommended_esi": "",
            "rationale": "",
            "immediate_interventions": [],
            "notes": "",
            "summary": ""  # Add a summary field
        }
        
        # Extract sections using regex
        impression_match = re.search(r'1\.\s*Initial Impression:(.*?)(?=2\.|\Z)', response, re.DOTALL)
        if impression_match:
            assessment["initial_impression"] = impression_match.group(1).strip()
        
        complaint_match = re.search(r'2\.\s*Chief Complaint.*?:(.*?)(?=3\.|\Z)', response, re.DOTALL)
        if complaint_match:
            assessment["chief_complaint"] = complaint_match.group(1).strip()
        
        findings_match = re.search(r'3\.\s*Concerning Findings:(.*?)(?=4\.|\Z)', response, re.DOTALL)
        if findings_match:
            assessment["concerning_findings"] = findings_match.group(1).strip()
        
        resources_match = re.search(r'4\.\s*Estimated Resource Needs:(.*?)(?=5\.|\Z)', response, re.DOTALL)
        if resources_match:
            assessment["resource_needs"] = resources_match.group(1).strip()
        
        esi_match = re.search(r'5\.\s*Recommended ESI Level:(.*?)(?=6\.|\Z)', response, re.DOTALL)
        if esi_match:
            assessment["recommended_esi"] = esi_match.group(1).strip()
        
        rationale_match = re.search(r'6\.\s*Rationale:(.*?)(?=7\.|\Z)', response, re.DOTALL)
        if rationale_match:
            assessment["rationale"] = rationale_match.group(1).strip()
        
        interventions_match = re.search(r'7\.\s*Immediate Nursing Interventions:(.*?)(?=8\.|\Z)', response, re.DOTALL)
        if interventions_match:
            interventions_text = interventions_match.group(1).strip()
            # Extract interventions as a list
            interventions_list = re.findall(r'(?:^|\n)\s*(?:-|\d+\.)\s*(.*?)(?=\n\s*(?:-|\d+\.)|\Z)', interventions_text, re.DOTALL)
            assessment["immediate_interventions"] = [i.strip() for i in interventions_list if i.strip()]
        
        notes_match = re.search(r'8\.\s*Additional Notes:(.*?)(?=\Z)', response, re.DOTALL)
        if notes_match:
            assessment["notes"] = notes_match.group(1).strip()
        
        # Extract ESI level from the recommended_esi field
        esi_digit_match = re.search(r'(\d+)', assessment["recommended_esi"])
        esi_level = esi_digit_match.group(1) if esi_digit_match else ""
        
        # Create a summary for display in the discussion
        assessment["summary"] = f"ESI Level: {esi_level}. Rationale: {assessment['rationale'][:100]}..."
        
        return assessment
    
    def _get_system_prompt(self):
        """Get the system prompt for the triage nurse agent"""
        # Load ESI examples - one per level
        esi_examples = load_esi_examples(num_per_level=1)
        
        # Format examples for triage nurse
        examples_text = format_examples_for_prompt(esi_examples, agent_type="nurse")
        
        base_prompt = """
        You are an experienced emergency department triage nurse with over 15 years of experience.
        Your role is to perform the initial assessment of patients and determine their Emergency Severity Index (ESI) level.
        
        When assessing a patient, focus on:
        1. Chief complaint and presenting symptoms with specific details (duration, severity, characteristics)
        2. Vital signs and their clinical significance
        3. Patient history relevant to the current presentation
        4. Risk factors specific to this patient
        5. Current level of distress with objective observations
        
        Provide specific, detailed observations rather than general statements. For example:
        - Instead of "patient has pain" → "patient reports sharp, stabbing chest pain radiating to left arm, 8/10 severity, started 2 hours ago while at rest"
        - Instead of "abnormal vital signs" → "tachycardic with HR 112, hypertensive at 162/94, afebrile at 98.6°F"
        
        Your assessment should be thorough and focused on objective clinical findings that impact ESI determination.
        
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