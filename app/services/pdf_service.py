import pdfplumber
import os
from typing import List, Dict, Any, Tuple
from app.core.config import settings


def extract_text_from_pdf(file_path: str) -> Tuple[str, List[Dict[str, Any]], int]:
    """
    Extract text from PDF with page references.
    Returns: (full_text, page_texts, page_count)
    """
    full_text = ""
    page_texts = []
    page_count = 0
    
    try:
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            
            if page_count > settings.MAX_PDF_PAGES:
                raise ValueError(f"PDF exceeds maximum page limit of {settings.MAX_PDF_PAGES}")
            
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    page_texts.append({
                        "page_number": i + 1,
                        "text": text
                    })
                    full_text += f"\n--- Page {i + 1} ---\n{text}"
        
        return full_text.strip(), page_texts, page_count
    
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_medical_facts(page_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract medical facts from page texts using simple pattern matching.
    In production, this would use NLP/ML models.
    """
    import re
    
    facts = []
    
    medication_patterns = [
        (r"(?i)(?:medication|drug|prescription|rx)[:\s]+([^\n]+)", "medication"),
        (r"(?i)(\w+(?:cillin|mycin|azole|pril|sartan|olol|pine|ide|ate|ium))\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml))", "medication_dose"),
        (r"(?i)(?:take|administer)[:\s]+([^\n]+)", "instruction"),
        (r"(?i)(?:dose|dosage)[:\s]+([^\n]+)", "dose"),
        (r"(?i)(?:frequency|freq)[:\s]+([^\n]+)", "frequency"),
        (r"(?i)(?:route|via)[:\s]+([^\n]+)", "route"),
        (r"(?i)(?:duration|for)[:\s]+([^\n]+)", "duration"),
        (r"(?i)(?:start|begin)[:\s]+([^\n]+)", "start_date"),
        (r"(?i)(?:stop|end|discontinue)[:\s]+([^\n]+)", "end_date"),
        (r"(?i)(?:diagnosis|dx)[:\s]+([^\n]+)", "diagnosis"),
        (r"(?i)(?:allergy|allergies)[:\s]+([^\n]+)", "allergy"),
    ]
    
    for page in page_texts:
        page_num = page["page_number"]
        text = page["text"]
        
        for pattern, fact_type in medication_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                source_text = match.group(0)
                extracted_value = match.group(1) if match.groups() else match.group(0)
                
                uncertainty = None
                if fact_type in ["dose", "frequency", "route", "duration", "start_date", "end_date"]:
                    if not extracted_value or len(extracted_value.strip()) < 2:
                        uncertainty = "Extracted value appears incomplete"
                
                facts.append({
                    "page_number": page_num,
                    "section": None,
                    "source_text": source_text.strip(),
                    "fact_type": fact_type,
                    "extracted_value": extracted_value.strip(),
                    "uncertainty_reason": uncertainty,
                })
    
    return facts


def validate_pdf_file(file_path: str) -> bool:
    """Validate that the file is a valid PDF."""
    try:
        with pdfplumber.open(file_path) as pdf:
            _ = len(pdf.pages)
        return True
    except Exception:
        return False