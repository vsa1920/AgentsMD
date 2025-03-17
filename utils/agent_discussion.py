import re
import json
import os
from datetime import datetime
from utils.query_model import query_model
from utils.esi_examples import load_esi_examples, format_examples_for_prompt
from utils.schema import ConsensusResult
from utils.structured_parser import parse_structured_output

class AgentDiscussion:
    def __init__(self, agents, model="o1-mini", api_key=None, max_rounds=3):
        """
        Initialize the Agent Discussion framework
        
        Args:
            agents (list): List of agent objects
            model (str): LLM model to use
            api_key (str): API key for the LLM service
            max_rounds (int): Maximum number of discussion rounds
        """
        self.agents = agents
        self.model = model
        self.api_key = api_key
        self.max_rounds = max_rounds
        
        # ESI level descriptions for reference
        self.esi_descriptions = {
            "1": "Requires immediate life-saving intervention",
            "2": "High risk situation; severe pain/distress",
            "3": "Requires multiple resources but stable vital signs",
            "4": "Requires one resource",
            "5": "Requires no resources"
        }
    
    def deliberate(self, conversation_text, case_id=None, progress_callback=None):
        """
        Conduct a deliberation among agents to determine ESI level
        
        Args:
            conversation_text (str): The text of the conversation
            case_id (str, optional): Case identifier
            progress_callback (callable, optional): Callback function to report progress
            
        Returns:
            dict: Results of the deliberation
        """
        # Initialize discussion
        discussion_history = []
        
        # Initial assessments
        if progress_callback:
            progress_callback("Triage Nurse is analyzing the conversation...", 15)
        
        nurse_assessment = self.agents[0].assess_conversation(conversation_text)
        
        if progress_callback:
            # Get a summary from the assessment, safely handling different formats
            nurse_summary = nurse_assessment.get('summary', 'Assessment completed')
            progress_callback(f"Triage Nurse: {nurse_summary[:100]}...", 25)
        
        if progress_callback:
            progress_callback("Emergency Physician is evaluating the case...", 35)
        
        physician_assessment = self.agents[1].assess_conversation(conversation_text)
        
        if progress_callback:
            # Get a summary from the assessment, safely handling different formats
            physician_summary = physician_assessment.get('summary', 'Assessment completed')
            progress_callback(f"Emergency Physician: {physician_summary[:100]}...", 45)
        
        if progress_callback:
            progress_callback("Medical Consultant is reviewing the case...", 55)
        
        consultant_assessment = self.agents[2].assess_conversation(conversation_text)
        
        if progress_callback:
            # Get a summary from the assessment, safely handling different formats
            consultant_summary = consultant_assessment.get('summary', 'Assessment completed')
            progress_callback(f"Medical Consultant: {consultant_summary[:100]}...", 65)
        
        # Add to discussion history
        discussion_history.append({
            "role": "Triage Nurse",
            "content": f"Initial assessment: {self._summarize_assessment(nurse_assessment)}"
        })
        discussion_history.append({
            "role": "Emergency Physician",
            "content": f"Initial assessment: {self._summarize_assessment(physician_assessment)}"
        })
        discussion_history.append({
            "role": "Medical Consultant",
            "content": f"Initial assessment: {self._summarize_assessment(consultant_assessment)}"
        })
        
        # Round 2: Agents respond to each other's assessments
        print("Round 2: Agents responding to each other's assessments...")
        
        # Create a dictionary of all assessments
        all_assessments = {
            self.agents[0].role: nurse_assessment,
            self.agents[1].role: physician_assessment,
            self.agents[2].role: consultant_assessment
        }
        
        for agent in self.agents:
            print(f"  - {agent.role} is responding to other assessments...")
            response = agent.respond_to_assessments(conversation_text, all_assessments)
            
            # Add to discussion history
            discussion_history.append({
                "role": agent.role,
                "content": response
            })
        
        # Round 3: Final deliberation and consensus
        print("Round 3: Final deliberation and consensus...")
        consensus_prompt = self._create_consensus_prompt(discussion_history, conversation_text)
        
        consensus_result = query_model(
            model_str=self.model,
            system_prompt=self._get_consensus_system_prompt(),
            prompt=consensus_prompt,
            openai_api_key=self.api_key
        )
        
        # Parse the consensus result
        final_result = parse_structured_output(consensus_result, ConsensusResult)
        
        # Add discussion summary
        final_result["discussion_summary"] = self._generate_discussion_summary(discussion_history)
        
        # Save the full discussion to a file
        self._save_discussion(discussion_history, case_id, final_result)
        
        # During discussion
        if progress_callback:
            progress_callback("Agents are discussing ESI determination...", 75)
        
        # After reaching consensus
        if progress_callback:
            progress_callback(f"Consensus reached: ESI Level {final_result['esi_level']} with {final_result['confidence']}% confidence", 85)
        
        return final_result
    
    def _save_discussion(self, discussion_history, case_id, final_result):
        """Save the full discussion to a file"""
        # Create discussions directory if it doesn't exist
        os.makedirs("discussions", exist_ok=True)
        
        # Format the discussion for saving
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"discussions/{case_id}_{timestamp}.txt"
        
        with open(filename, "w") as f:
            f.write(f"CASE ID: {case_id}\n")
            f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n\n")
            f.write("FULL AGENT DISCUSSION:\n")
            f.write("="*80 + "\n\n")
            
            for entry in discussion_history:
                f.write(f"[{entry['role']}]\n")
                f.write(f"{entry['content']}\n\n")
                f.write("-"*80 + "\n\n")
            
            f.write("="*80 + "\n\n")
            f.write("FINAL CONSENSUS:\n")
            f.write(f"ESI Level: {final_result['esi_level']}\n")
            f.write(f"Confidence: {final_result['confidence']}%\n")
            f.write(f"Justification: {final_result['justification']}\n\n")
            f.write("Recommended Actions:\n")
            for action in final_result['recommended_actions']:
                f.write(f"- {action}\n")
        
        print(f"Full discussion saved to {filename}")
        
        return filename
    
    def _summarize_assessment(self, assessment):
        """Create a summary of an agent's assessment"""
        # If the assessment already has a summary, use it
        if assessment.get('summary') and 'ESI Level' in assessment.get('summary'):
            return assessment['summary']
        
        # Otherwise, try to create a summary based on available fields
        esi_level = ""
        
        # Try multiple ways to extract ESI level
        if assessment.get('recommended_esi'):
            esi_match = re.search(r'(\d+)', assessment['recommended_esi'])
            if esi_match:
                esi_level = esi_match.group(1)
        elif assessment.get('esi_level'):
            esi_match = re.search(r'(\d+)', assessment['esi_level'])
            if esi_match:
                esi_level = esi_match.group(1)
        elif assessment.get('esi_evaluation'):
            esi_match = re.search(r'(\d+)', assessment['esi_evaluation'])
            if esi_match:
                esi_level = esi_match.group(1)
        
        # If we still don't have an ESI level, search through all fields
        if not esi_level:
            for key, value in assessment.items():
                if isinstance(value, str) and ('ESI' in value or 'esi' in value.lower()) and re.search(r'(\d+)', value):
                    esi_match = re.search(r'(\d+)', value)
                    esi_level = esi_match.group(1)
                    break
        
        # Get a rationale or assessment
        rationale = ""
        if assessment.get('rationale'):
            rationale = assessment['rationale'][:100]
        elif assessment.get('clinical_assessment'):
            rationale = assessment['clinical_assessment'][:100]
        elif assessment.get('specialist_impression'):
            rationale = assessment['specialist_impression'][:100]
        elif assessment.get('initial_impression'):
            rationale = assessment['initial_impression'][:100]
        
        # If we still don't have a rationale, use any non-empty string field
        if not rationale:
            for key, value in assessment.items():
                if isinstance(value, str) and len(value) > 10 and key not in ['summary', 'recommended_esi', 'esi_level', 'esi_evaluation']:
                    rationale = value[:100]
                    break
        
        # If we still don't have an ESI level, try to extract it from the rationale
        if not esi_level and rationale:
            esi_match = re.search(r'ESI\s*(?:level)?\s*(\d+)', rationale, re.IGNORECASE)
            if esi_match:
                esi_level = esi_match.group(1)
        
        # Create a default ESI level if we still don't have one
        if not esi_level:
            # Look for keywords in the assessment that might indicate severity
            severity_indicators = {
                "1": ["immediate", "life-saving", "critical", "unstable", "unresponsive", "cardiac arrest", "respiratory arrest"],
                "2": ["high risk", "severe pain", "severe distress", "abnormal vital signs", "altered mental status"],
                "3": ["multiple resources", "stable vital signs", "moderate symptoms"],
                "4": ["one resource", "minor", "simple"],
                "5": ["no resources", "minimal", "routine"]
            }
            
            # Convert assessment to a single string for keyword searching
            assessment_text = " ".join([str(v) for v in assessment.values() if isinstance(v, (str, list))])
            assessment_text = assessment_text.lower()
            
            # Check for severity indicators
            for level, indicators in severity_indicators.items():
                if any(indicator in assessment_text for indicator in indicators):
                    esi_level = level
                    break
        
        if esi_level and rationale:
            return f"ESI Level: {esi_level}. Rationale: {rationale}..."
        elif esi_level:
            return f"ESI Level: {esi_level}. No detailed rationale provided."
        elif rationale:
            return f"No ESI level specified. Assessment: {rationale}..."
        else:
            return "Assessment completed but no ESI level or rationale found."
    
    def _create_consensus_prompt(self, discussion_history, conversation_text):
        """Create a prompt for the final consensus"""
        prompt = [
            "Based on the patient-nurse conversation and the discussion between medical professionals below, "
            "determine the most appropriate ESI (Emergency Severity Index) level for this patient.",
            "",
            "PATIENT-NURSE CONVERSATION:",
            conversation_text,
            "",
            "DISCUSSION TRANSCRIPT:"
        ]
        
        for entry in discussion_history:
            prompt.append(f"{entry['role']}: {entry['content']}")
        
        prompt.append("")
        prompt.append("Please analyze the discussion and determine:")
        prompt.append("1. The final ESI level (1-5)")
        prompt.append("2. Confidence level (0-100%)")
        prompt.append("3. Clinical justification for this ESI level that references specific findings from this case")
        prompt.append("4. Recommended immediate actions (provide at least 3-5 specific actions)")
        prompt.append("")
        prompt.append("IMPORTANT: Your recommended actions MUST be specific to this patient's condition and presentation.")
        prompt.append("Do NOT provide generic recommendations like 'establish IV access' or 'monitor vital signs' without specifying WHY and HOW these actions relate to this specific patient.")
        prompt.append("Each recommendation should include the specific reason for the action based on the patient's symptoms or condition.")
        
        return "\n".join(prompt)
    
    def _get_consensus_system_prompt(self):
        """Get the system prompt for the consensus model"""
        # Load ESI examples - one per level
        esi_examples = load_esi_examples(num_per_level=1)
        
        # Format examples for consensus
        examples_text = format_examples_for_prompt(esi_examples, agent_type="consensus")
        
        return f"""
        You are an expert emergency medicine triage system that integrates the assessments of multiple medical professionals.
        Your task is to determine the final Emergency Severity Index (ESI) level for a patient based on the discussion among a triage nurse, emergency physician, and medical consultant.
        
        The Emergency Severity Index (ESI) is a five-level triage algorithm that categorizes patients by both acuity and resource needs:
        - ESI Level 1: Requires immediate life-saving intervention
        - ESI Level 2: High-risk situation, severe pain/distress, or vital sign abnormalities
        - ESI Level 3: Requires multiple resources but stable vital signs
        - ESI Level 4: Requires one resource
        - ESI Level 5: Requires no resources
        
        When determining the final ESI level:
        1. Consider all perspectives from the discussion
        2. Prioritize patient safety above all else
        3. Weigh clinical findings, vital signs, and risk factors
        4. Consider resource needs based on the patient's presentation
        5. Provide clear clinical justification for your decision
        
        REFERENCE EXAMPLES:
        
        {examples_text}
        
        Your output must follow this exact format:
        
        ESI Level: [1-5]
        Confidence: [0-100]%
        Clinical Justification: [Detailed explanation of why this ESI level is appropriate]
        Recommended Immediate Actions: [List of specific actions that should be taken]
        """
    
    def _parse_consensus_result(self, result):
        """Parse the consensus result into a structured format"""
        # Extract ESI level - try multiple patterns
        esi_match = re.search(r'(?:ESI Level|Level|Final ESI Level):\s*(\d)', result, re.IGNORECASE)
        if not esi_match:
            # Try to find any digit after ESI or Level
            esi_match = re.search(r'ESI.*?(\d)', result, re.IGNORECASE)
        if not esi_match:
            # Try to find any standalone digit that might be the ESI level
            esi_match = re.search(r'(?:^|\n|\s)(\d)(?:$|\n|\s)', result)
        
        # If we found a match, use it; otherwise default to level 3 (middle ground)
        esi_level = esi_match.group(1) if esi_match else "3"
        
        # Validate ESI level (must be 1-5)
        if esi_level not in ["1", "2", "3", "4", "5"]:
            # Default to level 3 if invalid
            esi_level = "3"
        
        # Extract confidence
        confidence_match = re.search(r'Confidence(?:\s*Level)?:\s*(\d+)%?', result, re.IGNORECASE)
        confidence = int(confidence_match.group(1)) if confidence_match else 80
        
        # Extract justification
        justification_match = re.search(r'(?:Justification|Clinical Justification|Rationale|Clinical Justification for ESI Level):(.*?)(?=Recommended(?:\s*Immediate)?\s*Actions|\Z)', result, re.DOTALL | re.IGNORECASE)
        justification = justification_match.group(1).strip() if justification_match else "No justification provided."
        
        # Extract recommended actions
        actions = []
        actions_match = re.search(r'Recommended(?:\s*Immediate)?\s*Actions:(.*?)(?=\Z|\n\s*\d+\.)', result, re.DOTALL | re.IGNORECASE)
        if actions_match:
            actions_text = actions_match.group(1).strip()
            # Extract actions as a list - look for bullet points or numbered items
            actions_list = re.findall(r'(?:^|\n)\s*(?:-|\d+\.)\s*(.*?)(?=\n\s*(?:-|\d+\.)|\Z)', actions_text, re.DOTALL)
            actions = [a.strip() for a in actions_list if a.strip() and not a.startswith("**")]
        
        # If no actions found or actions contain meta-instructions, try a different approach
        if not actions or any("**" in action for action in actions):
            # Look for any bullet points or numbered items in the entire text
            actions_list = re.findall(r'(?:^|\n)\s*(?:-|\d+\.)\s*(.*?)(?=\n\s*(?:-|\d+\.)|\Z)', result, re.DOTALL)
            # Filter out meta-instructions and keep only reasonable-length action items
            actions = [a.strip() for a in actions_list if a.strip() 
                      and not a.startswith("**") 
                      and "ESI Level" not in a 
                      and "Confidence" not in a
                      and "Justification" not in a
                      and "Recommended Actions" not in a
                      and len(a) < 200]  # Allow longer actions for more specificity
        
        # If still no actions, generate default actions based on ESI level and justification
        if not actions:
            # Extract key symptoms or conditions from the justification
            key_symptoms = []
            if "chest pain" in justification.lower():
                key_symptoms.append("chest pain")
            if "shortness of breath" in justification.lower() or "sob" in justification.lower():
                key_symptoms.append("respiratory distress")
            if "fever" in justification.lower():
                key_symptoms.append("fever")
            if "bleeding" in justification.lower():
                key_symptoms.append("bleeding")
            if "trauma" in justification.lower() or "injury" in justification.lower():
                key_symptoms.append("trauma")
            if "pain" in justification.lower():
                key_symptoms.append("pain")
            
            # Default symptom if none detected
            if not key_symptoms:
                key_symptoms = ["presenting condition"]
            
            # Generate more specific actions based on ESI level and symptoms
            if esi_level == "1":
                actions = [
                    f"Immediate intervention by emergency physician for {' and '.join(key_symptoms)}",
                    f"Prepare resuscitation equipment appropriate for {' and '.join(key_symptoms)}",
                    f"Establish two large-bore IV access for immediate medication administration and fluid resuscitation",
                    "Continuous cardiac monitoring and vital sign checks every 2-3 minutes",
                    f"Notify critical care team for possible ICU admission due to {' and '.join(key_symptoms)}"
                ]
            elif esi_level == "2":
                actions = [
                    f"Urgent assessment by emergency physician within 10 minutes to evaluate {' and '.join(key_symptoms)}",
                    "Establish IV access for medication and fluid administration",
                    "Continuous vital sign monitoring every 5-10 minutes",
                    f"Administer appropriate medication for {' and '.join(key_symptoms)} after physician assessment",
                    f"Order diagnostic studies specific to {' and '.join(key_symptoms)} including labs and imaging"
                ]
            elif esi_level == "3":
                actions = [
                    f"Assessment by emergency physician within 30 minutes to evaluate {' and '.join(key_symptoms)}",
                    "Obtain baseline vital signs and repeat every 1-2 hours",
                    f"Order diagnostic tests appropriate for {' and '.join(key_symptoms)}",
                    "Establish IV access if needed for medication administration",
                    f"Provide symptomatic treatment for {' and '.join(key_symptoms)} as ordered"
                ]
            elif esi_level == "4":
                actions = [
                    f"Assessment by provider within 60 minutes to evaluate {' and '.join(key_symptoms)}",
                    "Obtain baseline vital signs",
                    f"Focused examination of {' and '.join(key_symptoms)}",
                    f"Consider appropriate testing for {' and '.join(key_symptoms)} if clinically indicated",
                    f"Provide symptomatic relief for {' and '.join(key_symptoms)} as appropriate"
                ]
            else:  # ESI level 5
                actions = [
                    f"Assessment by provider when available to evaluate {' and '.join(key_symptoms)}",
                    "Obtain baseline vital signs once",
                    f"Focused examination of {' and '.join(key_symptoms)}",
                    f"Provide education on home management of {' and '.join(key_symptoms)}",
                    "Arrange appropriate follow-up care as needed"
                ]
        
        return {
            "esi_level": esi_level,
            "confidence": confidence,
            "justification": justification,
            "recommended_actions": actions
        }
    
    def _generate_discussion_summary(self, discussion_history):
        """Generate a summary of the discussion"""
        summary = []
        
        for entry in discussion_history:
            # Extract the first sentence or up to 100 characters
            content = entry["content"]
            first_sentence = content.split('.')[0] + '.'
            if len(first_sentence) > 100:
                first_sentence = first_sentence[:97] + '...'
            
            summary.append(f"{entry['role']}: {first_sentence}")
        
        return "\n".join(summary) 