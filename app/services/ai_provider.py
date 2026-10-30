import asyncio
import httpx
import json
from typing import List, Dict, Any, Optional
from app.core.config import settings


class AIProvider:
    """Base AI provider interface."""
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        raise NotImplementedError


class DemoAIProvider(AIProvider):
    """Deterministic demo AI provider for testing."""
    
    def __init__(self):
        self.delay = settings.DEMO_AI_RESPONSE_DELAY_MS / 1000.0
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        await asyncio.sleep(self.delay)
        
        last_message = messages[-1]["content"].lower() if messages else ""
        
        if "medication" in last_message or "remind" in last_message:
            return self._medication_response(context)
        elif "diagnosis" in last_message or "condition" in last_message:
            return self._diagnosis_response(context)
        elif "allergy" in last_message:
            return self._allergy_response(context)
        else:
            return self._general_response(context)
    
    def _medication_response(self, context: Optional[List[Dict[str, Any]]]) -> str:
        if not context:
            return "I don't have access to your medication records. Please upload a prescription first."
        
        meds = [c for c in context if c.get("fact_type") == "medication"]
        if not meds:
            return "I couldn't find specific medication information in your records."
        
        response = "Based on your uploaded documents, here are your medications:\n\n"
        for med in meds:
            response += f"- {med.get('extracted_value', 'Unknown')}\n"
            if med.get("uncertainty_reason"):
                response += f"  ⚠️ Note: {med['uncertainty_reason']}\n"
        
        response += "\nWould you like me to help you set up a medication reminder?"
        return response
    
    def _diagnosis_response(self, context: Optional[List[Dict[str, Any]]]) -> str:
        if not context:
            return "I don't have access to your medical records. Please upload a document first."
        
        diagnoses = [c for c in context if c.get("fact_type") == "diagnosis"]
        if not diagnoses:
            return "I couldn't find specific diagnosis information in your records."
        
        response = "Based on your uploaded documents:\n\n"
        for dx in diagnoses:
            response += f"- {dx.get('extracted_value', 'Unknown')}\n"
        
        return response
    
    def _allergy_response(self, context: Optional[List[Dict[str, Any]]]) -> str:
        if not context:
            return "I don't have access to your allergy records."
        
        allergies = [c for c in context if c.get("fact_type") == "allergy"]
        if not allergies:
            return "No allergies documented in your uploaded records."
        
        response = "Your documented allergies:\n\n"
        for allergy in allergies:
            response += f"- {allergy.get('extracted_value', 'Unknown')}\n"
        
        return response
    
    def _general_response(self, context: Optional[List[Dict[str, Any]]]) -> str:
        if not context:
            return "I don't have access to your medical records yet. Please upload a prescription or medical document to get started."
        
        fact_types = set(c.get("fact_type", "unknown") for c in context)
        response = f"I have access to your records containing: {', '.join(fact_types)}.\n\n"
        response += "What would you like to know about your medical information?"
        return response


class NemotronProvider(AIProvider):
    """NVIDIA Nemotron AI provider."""
    
    def __init__(self):
        self.api_url = settings.NEMOTRON_API_URL
        self.api_key = settings.NEMOTRON_API_KEY
        self.model = settings.NEMOTRON_MODEL
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        if not self.api_key:
            raise ValueError("Nemotron API key not configured")
        
        system_prompt = self._build_system_prompt(context)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _build_system_prompt(self, context: Optional[List[Dict[str, Any]]]) -> str:
        prompt = """You are CarePilot AI, a personal healthcare assistant. 
You must only use the provided context to answer questions.
Never invent medical information, dosages, or instructions.
If the context doesn't contain the answer, say so clearly.
Always cite your sources by referencing the document and page."""
        
        if context:
            prompt += "\n\nAuthorized Context:\n"
            for i, item in enumerate(context):
                prompt += f"[{i+1}] Page {item.get('page_number', '?')}: {item.get('source_text', '')[:200]}\n"
        
        return prompt


def get_ai_provider() -> AIProvider:
    if settings.AI_PROVIDER == "nemotron" and settings.NEMOTRON_API_KEY:
        return NemotronProvider()
    return DemoAIProvider()