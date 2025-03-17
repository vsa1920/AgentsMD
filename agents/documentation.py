import re
import json
from datetime import datetime
from utils.query_model import query_model

class DocumentationAgent:
    def __init__(self, model="o1-mini", api_key=None):
        """
        Initialize the Documentation Agent
        
        Args:
            model (str): LLM model to use
            api_key (str): API key for the LLM service
        """
        self.model = model
        self.api_key = api_key
        self.role = "Documentation Specialist"
    
    def generate_report(self, case_id, timestamp, clinical_data, nurse_assessment, physician_assessment, esi_result):
        """
        Generate a comprehensive triage report
        
        Args:
            case_id (str): Unique case identifier
            timestamp (datetime): Time of assessment
            clinical_data (dict): Extracted clinical data
            nurse_assessment (dict): Triage nurse assessment
            physician_assessment (dict): Emergency physician assessment
            esi_result (dict): ESI classification result
            
        Returns:
            str: Formatted triage report
        """
        # Create a system prompt for the documentation role
        system_prompt = """
        You are an experienced medical documentation specialist with expertise in emergency department triage.
        Your task is to generate a comprehensive, well-structured triage report based on the provided information.
        
        The report should:
        1. Be professionally formatted and use proper medical terminology
        2. Include all relevant clinical information
        3. Clearly state the ESI level and justification
        4. Summarize the assessments from both the triage nurse and emergency physician
        5. Include recommended actions and next steps
        
        Be thorough but concise, focusing on the most critical aspects of the case.
        """
        
        # Format all the data for the prompt
        formatted_data = self._format_data(
            case_id, 
            timestamp, 
            clinical_data, 
            nurse_assessment, 
            physician_assessment, 
            esi_result
        )
        
        # Create the user prompt
        user_prompt = f"""
        Please generate a comprehensive triage report based on the following information:
        
        {formatted_data}
        
        Format the report professionally with clear sections including:
        - Patient Information
        - Clinical Presentation
        - Triage Assessment
        - ESI Classification
        - Recommended Actions
        - Disposition
        """
        
        # Query the model
        response = query_model(
            model_str=self.model,
            system_prompt=system_prompt,
            prompt=user_prompt,
            openai_api_key=self.api_key
        )
        
        return response
    
    def _format_data(self, case_id, timestamp, clinical_data, nurse_assessment, physician_assessment, esi_result):
        """Format all data for the prompt"""
        formatted = []
        
        # Add case information
        formatted.append(f"CASE ID: {case_id}")
        formatted.append(f"TIMESTAMP: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add patient information
        formatted.append("\nPATIENT INFORMATION:")
        formatted.append(f"Age: {clinical_data.get('age', 'Unknown')}")
        formatted.append(f"Gender: {clinical_data.get('gender', 'Unknown')}")
        
        # Add clinical data
        formatted.append("\nCLINICAL DATA:")
        formatted.append(f"Chief Complaint: {clinical_data.get('chief_complaint', 'Unknown')}")
        
        # Add vital signs
        vitals = clinical_data.get('vital_signs', {})
        if vitals:
            formatted.append("Vital Signs:")
            if 'temperature' in vitals:
                formatted.append(f"- Temperature: {vitals['temperature']}°C")
            if 'heart_rate' in vitals:
                formatted.append(f"- Heart Rate: {vitals['heart_rate']} bpm")
            if 'respiratory_rate' in vitals:
                formatted.append(f"- Respiratory Rate: {vitals['respiratory_rate']} breaths/min")
            if 'blood_pressure_systolic' in vitals and 'blood_pressure_diastolic' in vitals:
                formatted.append(f"- Blood Pressure: {vitals['blood_pressure_systolic']}/{vitals['blood_pressure_diastolic']} mmHg")
            if 'oxygen_saturation' in vitals:
                formatted.append(f"- Oxygen Saturation: {vitals['oxygen_saturation']}%")
            if 'pain_level' in vitals:
                formatted.append(f"- Pain Level: {vitals['pain_level']}/10")
        
        # Add symptoms
        symptoms = clinical_data.get('symptoms', [])
        if symptoms:
            formatted.append("\nSymptoms:")
            for symptom in symptoms:
                formatted.append(f"- {symptom}")
        
        # Add medical history
        history = clinical_data.get('medical_history', [])
        if history:
            formatted.append("\nMedical History:")
            for item in history:
                formatted.append(f"- {item}")
        
        # Add allergies
        allergies = clinical_data.get('allergies', [])
        if allergies:
            formatted.append("\nAllergies:")
            for allergy in allergies:
                formatted.append(f"- {allergy}")
        
        # Add medications
        medications = clinical_data.get('medications', [])
        if medications:
            formatted.append("\nMedications:")
            for medication in medications:
                formatted.append(f"- {medication}")
        
        # Add nurse assessment
        formatted.append("\nTRIAGE NURSE ASSESSMENT:")
        formatted.append(f"Initial Impression: {nurse_assessment.get('initial_impression', 'Not provided')}")
        formatted.append(f"Vital Signs Assessment: {nurse_assessment.get('vital_signs_assessment', 'Not provided')}")
        formatted.append(f"Chief Complaint Severity: {nurse_assessment.get('chief_complaint_severity', 'Not provided')}")
        formatted.append(f"Estimated Resource Needs: {nurse_assessment.get('resource_needs', 'Not provided')}")
        formatted.append(f"Recommended ESI Level: {nurse_assessment.get('recommended_esi', 'Not provided')}")
        formatted.append(f"Rationale: {nurse_assessment.get('rationale', 'Not provided')}")
        
        # Add physician assessment
        formatted.append("\nEMERGENCY PHYSICIAN ASSESSMENT:")
        formatted.append(f"Clinical Assessment: {physician_assessment.get('clinical_assessment', 'Not provided')}")
        
        # Add potential diagnoses
        diagnoses = physician_assessment.get('potential_diagnoses', [])
        if diagnoses:
            formatted.append("Potential Diagnoses:")
            for i, diagnosis in enumerate(diagnoses, 1):
                formatted.append(f"{i}. {diagnosis}")
        
        formatted.append(f"ESI Level Assessment: {physician_assessment.get('esi_level', 'Not provided')}")
        
        # Add immediate actions
        actions = physician_assessment.get('immediate_actions', [])
        if actions:
            formatted.append("Immediate Actions:")
            for i, action in enumerate(actions, 1):
                formatted.append(f"{i}. {action}")
        
        # Add diagnostic studies
        studies = physician_assessment.get('diagnostic_studies', [])
        if studies:
            formatted.append("Diagnostic Studies:")
            for i, study in enumerate(studies, 1):
                formatted.append(f"{i}. {study}")
        
        formatted.append(f"Risk Assessment: {physician_assessment.get('risk_assessment', 'Not provided')}")
        formatted.append(f"Disposition: {physician_assessment.get('disposition', 'Not provided')}")
        
        # Add ESI result
        formatted.append("\nFINAL ESI CLASSIFICATION:")
        formatted.append(f"ESI Level: {esi_result.get('level', 'Not determined')}")
        formatted.append(f"Confidence: {esi_result.get('confidence', 'N/A')}%")
        formatted.append(f"Justification: {esi_result.get('justification', 'Not provided')}")
        
        # Add recommended actions
        actions = esi_result.get('recommended_actions', [])
        if actions:
            formatted.append("Recommended Actions:")
            for i, action in enumerate(actions, 1):
                formatted.append(f"{i}. {action}")
        
        return "\n".join(formatted) 