from pydantic import BaseModel
from typing import List, Optional

class TriageAssessment(BaseModel):
    """Pydantic model for triage nurse assessment"""
    initial_impression: str
    chief_complaint: str
    concerning_findings: str
    resource_needs: str
    recommended_esi: str
    rationale: str
    immediate_interventions: List[str]
    notes: str
    summary: str

class EmergencyAssessment(BaseModel):
    """Pydantic model for emergency physician assessment"""
    clinical_assessment: str
    potential_diagnoses: List[str]
    esi_level: str
    immediate_actions: List[str]
    diagnostic_studies: List[str]
    risk_assessment: str
    disposition: str
    summary: str

class ConsultantAssessment(BaseModel):
    """Pydantic model for medical consultant assessment"""
    specialist_impression: str
    differential_considerations: List[str]
    esi_evaluation: str
    specialized_recommendations: List[str]
    potential_pitfalls: str
    additional_insights: str
    summary: str

class ESIResult(BaseModel):
    """Pydantic model for final ESI classification"""
    level: str
    confidence: float
    justification: str
    recommended_actions: List[str]

class ConsensusResult(BaseModel):
    """Pydantic model for ESI consensus output format
    
    This model represents the exact format required for consensus output:
    ESI Level: [1-5]
    Confidence: [0-100]%
    Clinical Justification: [Detailed explanation]
    Recommended Immediate Actions: [List of actions]
    """
    esi_level: str
    confidence: int
    clinical_justification: str
    justification: str
    recommended_actions: List[str]
    

class ClinicalData(BaseModel):
    """Pydantic model for patient clinical data"""
    age: Optional[str]
    gender: Optional[str]
    chief_complaint: Optional[str]
    vital_signs: Optional[dict]
    symptoms: Optional[List[str]]
    medical_history: Optional[List[str]]
    allergies: Optional[List[str]]
    medications: Optional[List[str]]

class AgentAssessments(BaseModel):
    """Pydantic model for collecting assessments from all agents"""
    triage_nurse: Optional[TriageAssessment]
    emergency_physician: Optional[EmergencyAssessment]
    medical_consultant: Optional[ConsultantAssessment]
    esi_result: Optional[ESIResult]
    clinical_data: Optional[ClinicalData] 