import os
import argparse
import json
from datetime import datetime

# Import using direct paths
import sys
sys.path.append('.')  # Add current directory to path

from agents.triage_nurse import TriageNurseAgent
from agents.emergency_physician import EmergencyPhysicianAgent
from agents.medical_consultant import MedicalConsultantAgent
from utils.agent_discussion import AgentDiscussion
from utils.schema import AgentAssessments, ESIResult, ClinicalData

class ClinicalTriageSystem:
    def __init__(self, api_key=None, llm_backend="o1-mini", verbose=False):
        """
        Initialize the Clinical Triage System
        
        Args:
            api_key (str): API key for the LLM service
            llm_backend (str): LLM model to use
            verbose (bool): Whether to print verbose output
        """
        self.api_key = api_key
        self.llm_backend = llm_backend
        self.verbose = verbose
        
        # Set output directories
        self.output_dirs = {
            "results": "results",
            "discussions": "discussions",
            "quick_ref": "quick_ref"
        }
        
        # Initialize agents
        self.triage_nurse = TriageNurseAgent(model=llm_backend, api_key=api_key)
        self.emergency_physician = EmergencyPhysicianAgent(model=llm_backend, api_key=api_key)
        self.medical_consultant = MedicalConsultantAgent(model=llm_backend, api_key=api_key)
        
        # Initialize discussion framework
        self.agents = [self.triage_nurse, self.emergency_physician, self.medical_consultant]
        self.discussion = AgentDiscussion(
            agents=[self.triage_nurse, self.emergency_physician, self.medical_consultant],
            model=llm_backend,
            api_key=api_key
        )
        
        # Initialize assessment results
        self.assessment_results = None
        self.case_id = None
    
    def _generate_case_id(self):
        """Generate a unique case ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"CASE-{timestamp}"
    
    def process_conversation(self, conversation_text):
        """
        Process a patient-nurse conversation through agent discussion
        
        Args:
            conversation_text (str): The text of the conversation
            
        Returns:
            dict: Triage assessment results with ESI level
        """
        # Generate a case ID if not already set
        if not self.case_id:
            self.case_id = self._generate_case_id()
        
        # Create a timestamp for this assessment
        current_timestamp = datetime.now()
        
        if self.verbose:
            print(f"Processing case {self.case_id}...")
            print("Beginning agent discussion for ESI determination...")
        
        # Conduct agent discussion to determine ESI level
        discussion_result = self.discussion.deliberate(
            conversation_text=conversation_text,
            case_id=self.case_id
        )
        
        # Store and return results
        self.assessment_results = {
            "case_id": self.case_id,
            "timestamp": current_timestamp.isoformat(),
            "esi_level": discussion_result["esi_level"],
            "confidence": discussion_result["confidence"],
            "justification": discussion_result["justification"],
            "recommended_actions": discussion_result["recommended_actions"],
            "discussion_summary": discussion_result["discussion_summary"]
        }
        
        # Save the assessment results to a file
        self.save_assessment_results()
        
        # Generate quick reference for nurses
        self.generate_quick_reference()
        
        if self.verbose:
            print(f"ESI determination complete: Level {discussion_result['esi_level']}")
        
        return self.assessment_results
    
    def save_assessment_results(self):
        """Save the assessment results to a file"""
        # Create results directory if it doesn't exist
        os.makedirs(self.output_dirs["results"], exist_ok=True)
        
        # Format the results for saving
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dirs['results']}/{self.case_id}_{timestamp}.json"
        
        # Save as JSON
        with open(filename, 'w') as f:
            json.dump(self.assessment_results, f, indent=2)
        
        # Also save as human-readable text
        text_filename = f"{self.output_dirs['results']}/{self.case_id}_{timestamp}.txt"
        with open(text_filename, 'w') as f:
            f.write(f"Case ID: {self.case_id}\n")
            f.write(f"Timestamp: {timestamp}\n\n")
            f.write(f"ESI Level: {self.assessment_results['esi_level']}\n")
            f.write(f"Confidence: {self.assessment_results['confidence']}%\n\n")
            f.write(f"Justification:\n{self.assessment_results['justification']}\n\n")
            f.write("Recommended Actions:\n")
            for i, action in enumerate(self.assessment_results['recommended_actions'], 1):
                f.write(f"{i}. {action}\n")
        
        return text_filename
    
    def print_assessment(self):
        """Print the triage assessment in a formatted way"""
        if not self.assessment_results:
            print("No assessment has been performed yet.")
            return
        
        result = self.assessment_results
        
        print("\n" + "="*60)
        print(f"CLINICAL TRIAGE ASSESSMENT")
        print("="*60)
        print(f"Case ID: {result['case_id']}")
        print(f"Timestamp: {result['timestamp']}")
        print("\n")
        print(f"ESI LEVEL: {result['esi_level']}")
        print(f"Confidence: {result['confidence']}%")
        print("\n")
        print("CLINICAL JUSTIFICATION:")
        print(result['justification'])
        print("\n")
        print("RECOMMENDED ACTIONS:")
        for action in result['recommended_actions']:
            print(f"- {action}")
        print("\n")
        print("AGENT DISCUSSION SUMMARY:")
        print(result['discussion_summary'])
        print("="*60)

    def generate_quick_reference(self):
        """Generate a quick reference file for nurses in action"""
        from utils.quick_reference import generate_quick_reference
        
        # Extract chief complaint if available
        chief_complaint = None
        if hasattr(self, 'nurse_assessment') and self.nurse_assessment:
            chief_complaint = self.nurse_assessment.get('chief_complaint')
        
        # Generate the quick reference file
        quick_ref_file = generate_quick_reference(
            case_id=self.case_id,
            esi_level=self.assessment_results["esi_level"],
            confidence=self.assessment_results["confidence"],
            actions=self.assessment_results["recommended_actions"],
            chief_complaint=chief_complaint,
            output_dir=self.output_dirs["quick_ref"]  # Pass the custom directory
        )
        
        return quick_ref_file

    def generate_differential_diagnoses(self):
        """Generate potential differential diagnoses based on the assessment"""
        from utils.differential_diagnoses import generate_differential_diagnoses
        
        # Generate the differential diagnoses file
        diff_dx_file = generate_differential_diagnoses(
            case_id=self.case_id,
            assessment_results=self.assessment_results,
            output_dir="differential_diagnoses"  # Create a new directory for these files
        )
        
        return diff_dx_file

def main():
    parser = argparse.ArgumentParser(description="Clinical Triage System")
    parser.add_argument("--api-key", required=True, help="API key for LLM service")
    parser.add_argument("--input-file", help="Path to conversation text file")
    parser.add_argument("--input-text", help="Direct conversation text input")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Initialize the system
    triage_system = ClinicalTriageSystem(
        api_key=args.api_key,
        verbose=args.verbose
    )
    
    # Get conversation text
    conversation_text = ""
    if args.input_file:
        with open(args.input_file, 'r') as f:
            conversation_text = f.read()
    elif args.input_text:
        conversation_text = args.input_text
    else:
        print("Please provide conversation text via --input-file or --input-text")
        return
    
    # Process the conversation
    triage_system.process_conversation(conversation_text)
    
    # Print the assessment
    triage_system.print_assessment()

if __name__ == "__main__":
    main() 