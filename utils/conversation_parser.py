import re
import json
from datetime import datetime

class ConversationParser:
    def __init__(self):
        """Initialize the conversation parser"""
        # Regular expressions for extracting clinical data
        self.regex_patterns = {
            "age": r'(\d+)[\s-]*(?:year|yr)s?[\s-]*old',
            "temperature": r'(?:temp|temperature)[:\s]*(\d+\.?\d*)',
            "heart_rate": r'(?:hr|heart rate|pulse)[:\s]*(\d+)',
            "respiratory_rate": r'(?:rr|resp|respiratory rate)[:\s]*(\d+)',
            "blood_pressure": r'(?:bp|blood pressure)[:\s]*(\d+)[/](\d+)',
            "oxygen_saturation": r'(?:o2|oxygen|sat|saturation)[:\s]*(\d+)',
            "pain_level": r'pain[^.]*?(\d+)(?:/10)?',
        }
        
        # Keywords for symptom categorization
        self.symptom_categories = {
            "respiratory": ["cough", "shortness of breath", "sob", "dyspnea", "wheezing"],
            "cardiac": ["chest pain", "palpitations", "syncope", "edema"],
            "neurological": ["headache", "dizziness", "numbness", "tingling", "seizure"],
            "gastrointestinal": ["nausea", "vomiting", "diarrhea", "constipation", "abdominal pain"],
            "musculoskeletal": ["joint pain", "back pain", "fracture", "sprain", "injury"],
            "general": ["fever", "fatigue", "weakness", "malaise"]
        }
    
    def extract_clinical_data(self, conversation_text):
        """
        Extract clinical data from conversation text
        
        Args:
            conversation_text (str): The text of the conversation
            
        Returns:
            dict: Extracted clinical data
        """
        # Convert to lowercase for easier matching
        text = conversation_text.lower()
        
        # Initialize the data structure
        clinical_data = {
            "chief_complaint": self._extract_chief_complaint(text),
            "vital_signs": self._extract_vital_signs(text),
            "symptoms": self._extract_symptoms(text),
            "medical_history": self._extract_medical_history(text),
            "age": self._extract_age(text),
            "gender": self._extract_gender(text),
            "allergies": self._extract_allergies(text),
            "medications": self._extract_medications(text),
            "raw_conversation": conversation_text
        }
        
        return clinical_data
    
    def _extract_chief_complaint(self, text):
        """Extract the chief complaint from the conversation"""
        # Look for common phrases that introduce chief complaints
        patterns = [
            r'(?:chief complaint|cc|presenting with|here for|presenting for|reason for visit)[:\s]*([^.]+)',
            r'(?:complains of|complaining of)[:\s]*([^.]+)',
            r'(?:patient states|pt states)[:\s]*([^.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        # If no match found, try to extract the first symptom mentioned
        sentences = text.split('.')
        for sentence in sentences[:3]:  # Check first 3 sentences
            for symptom_list in self.symptom_categories.values():
                for symptom in symptom_list:
                    if symptom in sentence:
                        return f"{symptom} {sentence.split(symptom)[1].strip()}"
        
        return "Unknown"
    
    def _extract_vital_signs(self, text):
        """Extract vital signs from the conversation"""
        vital_signs = {}
        
        # Extract temperature
        temp_match = re.search(self.regex_patterns["temperature"], text)
        if temp_match:
            vital_signs["temperature"] = float(temp_match.group(1))
        
        # Extract heart rate
        hr_match = re.search(self.regex_patterns["heart_rate"], text)
        if hr_match:
            vital_signs["heart_rate"] = int(hr_match.group(1))
        
        # Extract respiratory rate
        rr_match = re.search(self.regex_patterns["respiratory_rate"], text)
        if rr_match:
            vital_signs["respiratory_rate"] = int(rr_match.group(1))
        
        # Extract blood pressure
        bp_match = re.search(self.regex_patterns["blood_pressure"], text)
        if bp_match:
            vital_signs["blood_pressure_systolic"] = int(bp_match.group(1))
            vital_signs["blood_pressure_diastolic"] = int(bp_match.group(2))
        
        # Extract oxygen saturation
        o2_match = re.search(self.regex_patterns["oxygen_saturation"], text)
        if o2_match:
            vital_signs["oxygen_saturation"] = int(o2_match.group(1))
        
        # Extract pain level
        pain_match = re.search(self.regex_patterns["pain_level"], text)
        if pain_match:
            vital_signs["pain_level"] = int(pain_match.group(1))
        
        return vital_signs
    
    def _extract_symptoms(self, text):
        """Extract symptoms from the conversation"""
        symptoms = []
        
        # Check for symptoms in each category
        for category, symptom_list in self.symptom_categories.items():
            for symptom in symptom_list:
                if symptom in text:
                    # Try to get context around the symptom
                    pattern = f"[^.]*{symptom}[^.]*"
                    matches = re.findall(pattern, text)
                    for match in matches:
                        symptoms.append(match.strip())
        
        return symptoms
    
    def _extract_medical_history(self, text):
        """Extract medical history from the conversation"""
        history = []
        
        # Look for common phrases that introduce medical history
        patterns = [
            r'(?:medical history|pmh|past medical history)[:\s]*([^.]+)',
            r'(?:history of|hx of)[:\s]*([^.]+)',
            r'(?:diagnosed with|dx with)[:\s]*([^.]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                history.append(match.strip())
        
        return history
    
    def _extract_age(self, text):
        """Extract patient age from the conversation"""
        age_match = re.search(self.regex_patterns["age"], text)
        if age_match:
            return int(age_match.group(1))
        return None
    
    def _extract_gender(self, text):
        """Extract patient gender from the conversation"""
        male_pattern = r'\b(?:male|man|boy|gentleman|he|him|his)\b'
        female_pattern = r'\b(?:female|woman|girl|lady|she|her|hers)\b'
        
        male_matches = re.findall(male_pattern, text)
        female_matches = re.findall(female_pattern, text)
        
        if len(male_matches) > len(female_matches):
            return "male"
        elif len(female_matches) > len(male_matches):
            return "female"
        else:
            return "unknown"
    
    def _extract_allergies(self, text):
        """Extract patient allergies from the conversation"""
        allergies = []
        
        # Look for common phrases that introduce allergies
        patterns = [
            r'(?:allergies|allergic to)[:\s]*([^.]+)',
            r'(?:allergy|allergic)[:\s]*([^.]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up common negations
                if "no known" in match.lower() or "nka" in match.lower():
                    allergies.append("No known allergies")
                else:
                    allergies.append(match.strip())
        
        return allergies if allergies else ["None documented"]
    
    def _extract_medications(self, text):
        """Extract patient medications from the conversation"""
        medications = []
        
        # Look for common phrases that introduce medications
        patterns = [
            r'(?:medications|meds|taking)[:\s]*([^.]+)',
            r'(?:prescribed|prescription)[:\s]*([^.]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean up common negations
                if "no " in match.lower() or "none" in match.lower():
                    medications.append("No medications")
                else:
                    medications.append(match.strip())
        
        return medications if medications else ["None documented"] 