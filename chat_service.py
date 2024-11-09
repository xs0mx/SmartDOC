from openai import OpenAI
from models import PatientDiagnosis, User
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from extensions import db

load_dotenv()

class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('sk-proj-iFLoG5VuiFt7s4qSqC-u7tLz-T-v4PGL18qegRnPyM1W6aX9FE9KRJQ2fRLIMTuobFMf67B22T3BlbkFJ6rnZ_rcEmEA3GHy-IKSxN3ya2dZ1jOmK0WtF8zF52jjHJLMrgkKOvAeKKdHSaQYFM5EOgyhnkA'))

    def analyze_severity(self, message, patient_context):
        """Analyze the severity of symptoms and generate a priority rating"""
        try:
            severity_prompt = [
                {"role": "system", "content": f"""
                You are a medical severity assessment AI. Based on the patient's message and medical history:
                1. Analyze the symptoms described
                2. Consider the patient's existing conditions: {json.dumps(patient_context)}
                3. Generate a priority rating from 1-99%
                4. Return JSON format with:
                   - priority_rating (number)
                   - reasoning (string)
                   - recommended_action (string)
                   - timeframe (string)

                Priority Rating Guide:
                90-99%: Immediate emergency attention needed
                70-89%: Urgent care within hours
                50-69%: Should see doctor within 24 hours
                30-49%: Should see doctor within few days
                1-29%: Routine care/monitoring

                Return only valid JSON.
                """},
                {"role": "user", "content": message}
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=severity_prompt,
                temperature=0.3,
                max_tokens=300
            )

            # Parse the response as JSON
            severity_analysis = json.loads(response.choices[0].message.content)
            
            # Save to database if priority is high
            if severity_analysis['priority_rating'] > 70:
                self.notify_doctor(patient_context, severity_analysis)
                
            return severity_analysis

        except Exception as e:
            print(f"Error in severity analysis: {str(e)}")
            return {
                "priority_rating": 50,
                "reasoning": "Error in severity analysis, defaulting to moderate priority",
                "recommended_action": "Please consult with healthcare provider",
                "timeframe": "As soon as possible"
            }

    def notify_doctor(self, patient_context, severity_analysis):
        """Create an urgent notification for the doctor"""
        try:
            from models import UrgentNotification  # Add this model definition
            
            notification = UrgentNotification(
                patient_id=patient_context.get('patient_id'),
                priority_rating=severity_analysis['priority_rating'],
                reasoning=severity_analysis['reasoning'],
                recommended_action=severity_analysis['recommended_action'],
                timeframe=severity_analysis['timeframe'],
                timestamp=datetime.utcnow()
            )
            db.session.add(notification)
            db.session.commit()
        except Exception as e:
            print(f"Error saving notification: {str(e)}")

    def get_patient_context(self, patient):
        diagnoses = PatientDiagnosis.query.filter_by(patient_id=patient.id).all()
        context = []
        for diagnosis in diagnoses:
            context.append({
                'patient_id': patient.id,
                'diagnosis': diagnosis.diagnosis,
                'treatment': diagnosis.treatment,
                'medications': diagnosis.medications,
                'date': diagnosis.date.strftime('%Y-%m-%d')
            })
        return context

    def get_chat_response(self, patient, message):
        try:
            context = self.get_patient_context(patient)
            
            # First analyze severity
            severity_analysis = self.analyze_severity(message, context)
            
            # Create chat prompt with severity awareness
            prompt = [
                {"role": "system", "content": f"""
                You are an AI Medical Assistant. Current context:
                - Patient History: {json.dumps(context)}
                - Current Severity Rating: {severity_analysis['priority_rating']}%
                
                Guidelines:
                1. Be compassionate and professional
                2. For severity {severity_analysis['priority_rating']}% or higher, 
                   strongly encourage immediate medical attention
                3. Never provide medical advice that contradicts their treatment
                4. Explain their current medications if asked
                5. Use simple, clear language
                """},
                {"role": "user", "content": message}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                temperature=0.7,
                max_tokens=300
            )
            
            chat_response = response.choices[0].message.content
            
            # Add severity warning for high priority cases
            if severity_analysis['priority_rating'] > 70:
                chat_response += f"\n\nIMPORTANT: Based on your symptoms, this has been rated as {severity_analysis['priority_rating']}% priority. {severity_analysis['recommended_action']} {severity_analysis['timeframe']}."
            
            return chat_response
            
        except Exception as e:
            print(f"Error getting chat response: {str(e)}")
            return f"Error: {str(e)}"