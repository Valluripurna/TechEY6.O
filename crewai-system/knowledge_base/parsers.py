import fitz  # PyMuPDF
import docx2txt
import re
from typing import List
import os

def extract_text_from_pdf(path: str) -> str:
    """Extract text from PDF with enhanced error handling"""
    text = []
    try:
        with fitz.open(path) as doc:
            for page_num, page in enumerate(doc):
                try:
                    page_text = page.get_text()
                    if page_text.strip():
                        text.append(f"[PAGE {page_num + 1}]\n{page_text}")
                except Exception as e:
                    print(f"Warning: Could not extract text from page {page_num + 1} in {path}: {e}")
                    continue
        return "\n\n".join(text)
    except Exception as e:
        raise Exception(f"Error reading PDF file {path}: {str(e)}")

def extract_text_from_docx(path: str) -> str:
    """Extract text from DOCX with enhanced error handling"""
    try:
        text = docx2txt.process(path)
        if text:
            return text
        else:
            # Fallback: try to read as plain text
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    except Exception as e:
        raise Exception(f"Error reading DOCX file {path}: {str(e)}")

def extract_text_from_txt(path: str) -> str:
    """Extract text from TXT with enhanced error handling"""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error reading TXT file {path}: {str(e)}")

def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from file based on its extension
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: Extracted and cleaned text from the file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == '.pdf':
        raw_text = extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        raw_text = extract_text_from_docx(file_path)
    elif ext == '.txt':
        raw_text = extract_text_from_txt(file_path)
    else:
        # Try to read as text file for other extensions
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
        except Exception as e:
            print(f"Unsupported file type {ext} for file {file_path}: {str(e)}")
            return ""
    
    return clean_text(raw_text)

def clean_text(text: str) -> str:
    """Enhanced text cleaning for better processing"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might interfere with processing (but keep common punctuation)
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'\/\\\%\@\#\$\&\*\+\=\<\>\~\`\|\^]', ' ', text)
    
    # Normalize quotation marks
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    
    # Remove excessive line breaks but preserve paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Trim and return
    return text.strip()

def extract_key_sections(text: str) -> dict:
    """Extract key sections from academic papers"""
    sections = {}
    
    # Common section headers in academic papers
    section_patterns = {
        'abstract': r'(?:abstract|summary)(?:\s*:)?\s*(.*?)(?=\n(?:introduction|methods|results|discussion|conclusion|references)|$)',
        'introduction': r'(?:introduction)(?:\s*:)?\s*(.*?)(?=\n(?:methods|results|discussion|conclusion|references)|$)',
        'methods': r'(?:methods|methodology)(?:\s*:)?\s*(.*?)(?=\n(?:results|discussion|conclusion|references)|$)',
        'results': r'(?:results|findings)(?:\s*:)?\s*(.*?)(?=\n(?:discussion|conclusion|references)|$)',
        'discussion': r'(?:discussion)(?:\s*:)?\s*(.*?)(?=\n(?:conclusion|references)|$)',
        'conclusion': r'(?:conclusion)(?:\s*:)?\s*(.*?)(?=\n(?:references)|$)',
        'references': r'(?:references|bibliography)(?:\s*:)?\s*(.*?)(?=$)'
    }
    
    text_lower = text.lower()
    
    for section_name, pattern in section_patterns.items():
        match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
        if match:
            sections[section_name] = match.group(1).strip()
    
    return sections