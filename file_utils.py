"""File extraction and text preprocessing utilities."""

import os
import re
import subprocess
import traceback
from typing import Dict, List

from config import logger, SYNONYMS, THEME_KEYWORDS, STOPWORDS
from docx import Document
from PyPDF2 import PdfReader


def allowed_file(filename: str, allowed_extensions=None) -> bool:
    """Check if file extension is allowed."""
    if allowed_extensions is None:
        allowed_extensions = {'txt', 'pdf', 'doc', 'docx', 'rtf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from PDF using multiple methods for reliability."""
    text = ""

    # Method 1: Try PyPDF2 (most common)
    try:
        reader = PdfReader(filepath)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        if len(text.strip()) > 50:
            logger.info(f"✅ PyPDF2 extracted {len(text)} chars")
            return text
    except Exception as e:
        logger.warning(f"PyPDF2 failed: {e}")

    # Method 2: Try pdfplumber if available (better for complex PDFs)
    text = ""
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    text += page_text + "\n"

        if len(text.strip()) > 50:
            logger.info(f"✅ pdfplumber extracted {len(text)} chars")
            return text
    except ImportError:
        logger.warning("pdfplumber not installed")
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Method 3: Try tika if available (Apache Tika - most robust)
    try:
        from tika import parser
        parsed = parser.from_file(filepath)
        if parsed and parsed.get('content'):
            text = parsed['content']
            if len(text.strip()) > 50:
                logger.info(f"✅ Tika extracted {len(text)} chars")
                return text
    except ImportError:
        logger.warning("tika not installed")
    except Exception as e:
        logger.warning(f"Tika failed: {e}")

    # Method 4: Fallback - try to extract any text as bytes
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
            # Try to decode as text (might get garbage but better than nothing)
            text = raw.decode('utf-8', errors='ignore')
            # Clean up
            text = re.sub(r'[^\x20-\x7E\u0530-\u058F\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text)

            if len(text.strip()) > 50:
                logger.info(f"✅ Raw extraction got {len(text)} chars")
                return text
    except Exception as e:
        logger.warning(f"Raw extraction failed: {e}")

    logger.error(f"❌ All PDF extraction methods failed for {filepath}")
    return ""


def extract_text_from_docx(filepath: str) -> str:
    """Extract text from DOCX."""
    try:
        doc = Document(filepath)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        logger.info(f"✅ Extracted {len(text)} characters from DOCX")
        return text
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""


def extract_text_from_txt(filepath: str) -> str:
    """Extract text from TXT with encoding detection."""
    encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                text = f.read()
            logger.info(f"✅ Extracted {len(text)} characters from TXT using {enc}")
            return text
        except UnicodeDecodeError:
            continue
    logger.error("Could not decode TXT with any encoding")
    return ""


def load_text(filepath: str) -> str:
    """Main function to extract text from any supported format with better error handling."""
    try:
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return ""

        file_size = os.path.getsize(filepath)
        if file_size == 0:
            logger.error(f"File is empty: {filepath}")
            return ""

        extension = filepath.lower().split('.')[-1]
        logger.info(f"📄 Loading text from {os.path.basename(filepath)} (size: {file_size} bytes, type: {extension})")

        text = ""

        if extension == 'pdf':
            text = extract_text_from_pdf(filepath)
        elif extension == 'docx':
            text = extract_text_from_docx(filepath)
        elif extension == 'doc':
            # Try multiple methods for old DOC files
            try:
                # Method 1: Try antiword if available (best for old DOC)
                result = subprocess.run(['antiword', filepath], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout:
                    text = result.stdout
                else:
                    raise RuntimeError('antiword failed')
            except Exception:
                # Method 2: Fallback to raw text extraction
                try:
                    with open(filepath, 'rb') as f:
                        raw = f.read()
                        text = raw.decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.warning(f"Old DOC extraction failed: {e}")
        elif extension in ['txt', 'rtf']:
            text = extract_text_from_txt(filepath)
        else:
            logger.warning(f"Unsupported file type: {extension}")
            return ""

        # Validate extracted text
        if not text or len(text.strip()) < 20:
            logger.warning(f"❌ Extracted text too short ({len(text)} chars) from {filepath}")
            return ""

        # Clean the text
        text = re.sub(r'\s+', ' ', text).strip()
        logger.info(f"✅ Successfully extracted {len(text)} characters from {os.path.basename(filepath)}")

        return text

    except Exception as e:
        logger.error(f"Error loading file {filepath}: {e}")
        traceback.print_exc()
        return ""


def preprocess_text(text: str, use_synonyms: bool = True, remove_stopwords: bool = True) -> str:
    """Preprocess Armenian text."""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove numbers
    text = re.sub(r'\d+', ' ', text)

    # Keep only Armenian letters and spaces
    text = re.sub(r'[^ա-ֆ\s]', ' ', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove stopwords if requested
    if remove_stopwords and STOPWORDS:
        words = text.split()
        words = [w for w in words if w not in STOPWORDS]
        text = ' '.join(words)

    # Apply synonyms if requested
    if use_synonyms and SYNONYMS:
        words = text.split()
        normalized = []
        for word in words:
            replaced = False
            for main_word, synonyms in SYNONYMS.items():
                if word in synonyms:
                    normalized.append(main_word)
                    replaced = True
                    break
            if not replaced:
                normalized.append(word)
        text = ' '.join(normalized)

    return text


def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """Extract important keywords from text."""
    if not text:
        return []

    processed = preprocess_text(text, use_synonyms=False, remove_stopwords=True)
    words = processed.split()

    word_freq = {}
    for word in words:
        if len(word) >= 4:
            word_freq[word] = word_freq.get(word, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, _ in sorted_words[:max_keywords]]

    return keywords


def detect_theme(text: str):
    """Detect document theme based on keywords."""
    if not text or not THEME_KEYWORDS:
        return []

    text_lower = text.lower()
    theme_scores = {}

    for theme, keywords in THEME_KEYWORDS.items():
        score = 0
        matched = []
        for keyword in keywords:
            if keyword in text_lower:
                score += 1
                matched.append(keyword)
        if score > 0:
            theme_scores[theme] = {
                'score': score,
                'percentage': (score / len(keywords)) * 100,
                'matched_keywords': matched
            }

    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    return sorted_themes[:5]
