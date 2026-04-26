"""Similarity and highlighting utilities."""

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import logger, SEMANTIC_MODEL


def calculate_basic_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity based on word overlap."""
    if not text1 or not text2:
        return 0

    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return (len(intersection) / len(union)) * 100


def calculate_tfidf_similarity(text1: str, text2: str) -> float:
    """Calculate TF-IDF based similarity."""
    try:
        vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(3, 5),
            min_df=1,
            max_df=0.9
        )
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity) * 100
    except Exception as e:
        logger.warning(f"TF-IDF similarity failed: {e}")
        return calculate_basic_similarity(text1, text2)


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """Calculate semantic similarity using sentence transformers."""
    if SEMANTIC_MODEL:
        try:
            emb1 = SEMANTIC_MODEL.encode([text1[:1000]])[0]
            emb2 = SEMANTIC_MODEL.encode([text2[:1000]])[0]

            emb1 = emb1 / np.linalg.norm(emb1)
            emb2 = emb2 / np.linalg.norm(emb2)

            similarity = np.dot(emb1, emb2)
            return float(max(0, similarity * 100))
        except Exception as e:
            logger.warning(f"Semantic similarity failed: {e}")
            return calculate_tfidf_similarity(text1, text2)
    return calculate_tfidf_similarity(text1, text2)


def calculate_enhanced_similarity(text1: str, text2: str) -> dict:
    """Combine multiple similarity metrics."""
    from file_utils import preprocess_text

    processed1 = preprocess_text(text1, use_synonyms=True)
    processed2 = preprocess_text(text2, use_synonyms=True)

    basic_sim = calculate_basic_similarity(processed1, processed2)
    tfidf_sim = calculate_tfidf_similarity(processed1, processed2)
    semantic_sim = calculate_semantic_similarity(processed1, processed2)

    # Weighted combination
    combined = (basic_sim * 0.2) + (tfidf_sim * 0.3) + (semantic_sim * 0.5)
    combined = min(combined, 100)

    return {
        'basic_similarity': round(float(basic_sim), 1),
        'tfidf_similarity': round(float(tfidf_sim), 1),
        'semantic_similarity': round(float(semantic_sim), 1),
        'combined_similarity': round(float(combined), 1)
    }


def get_plagiarism_level(similarity: float) -> str:
    """Determine plagiarism level based on percentage."""
    if similarity >= 80:
        return "CRITICAL"
    elif similarity >= 60:
        return "HIGH"
    elif similarity >= 40:
        return "MODERATE"
    elif similarity >= 20:
        return "LOW"
    return "CLEAN"


def highlight_word_level(text1: str, text2: str) -> dict:
    """
    Create word-level highlighting for comparison.
    GUARANTEES that both file1 and file2 have a 'words' array for every sentence,
    even when similarity is 100% or an error occurs.
    """
    # Clean texts
    text1 = re.sub(r'\s+', ' ', text1).strip()
    text2 = re.sub(r'\s+', ' ', text2).strip()

    # Split into sentences
    sentences1 = re.split(r'[.!?…]+', text1)
    sentences2 = re.split(r'[.!?…]+', text2)

    # Filter out very short sentences (less than 5 chars)
    sentences1 = [s.strip() for s in sentences1 if len(s.strip()) > 5]
    sentences2 = [s.strip() for s in sentences2 if len(s.strip()) > 5]

    # Fallback: if no sentences, treat whole text as one sentence
    if not sentences1 and text1:
        sentences1 = [text1]
    if not sentences2 and text2:
        sentences2 = [text2]

    # If still empty, create dummy sentence to avoid empty UI
    if not sentences1:
        sentences1 = ["[No readable content in file 1]"]
    if not sentences2:
        sentences2 = ["[No readable content in file 2]"]

    result = {
        'file1': [],
        'file2': [],
        'matches': []
    }

    logger.info(f"📊 Highlighting: {len(sentences1)} sentences in file1, {len(sentences2)} in file2")

    # ------------------------------------------------------------
    # Helper to build word array from a sentence (always returns list)
    # ------------------------------------------------------------
    def build_word_array(sentence: str, plagiarized_flags=None):
        """Convert sentence into list of {text, plagiarized} dicts."""
        words = sentence.split()
        if not words:
            return [{'text': '', 'plagiarized': False}]
        if plagiarized_flags is None:
            plagiarized_flags = [False] * len(words)
        return [{'text': w, 'plagiarized': plagiarized_flags[i] if i < len(plagiarized_flags) else False} 
                for i, w in enumerate(words)]

    # ------------------------------------------------------------
    # Build matches for file1
    # ------------------------------------------------------------
    file2_to_file1 = {}   # map sentence index in file2 -> (file1_index, similarity)

    for i, sent1 in enumerate(sentences1):
        try:
            words1 = sent1.split()
            sent1_result = {
                'text': sent1,
                'words': [],
                'plagiarized': False,
                'similarity': 0,
                'matched_with': -1
            }

            best_match_idx = -1
            best_similarity = 0

            # Find best match in file2
            for j, sent2 in enumerate(sentences2):
                similarity = calculate_basic_similarity(sent1, sent2)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = j

            # Threshold for plagiarism (5%)
            if best_similarity > 5:
                sent1_result['plagiarized'] = True
                sent1_result['similarity'] = round(float(best_similarity), 1)
                sent1_result['matched_with'] = best_match_idx

                # Word-level marking for file1
                if best_match_idx >= 0 and best_match_idx < len(sentences2):
                    match_sent = sentences2[best_match_idx]
                    match_words = {w.lower() for w in match_sent.split() if len(w) >= 3}
                    word_flags = []
                    for word in words1:
                        word_lower = word.lower()
                        is_plag = len(word) >= 3 and best_similarity > 5 and word_lower in match_words
                        word_flags.append(is_plag)
                    sent1_result['words'] = build_word_array(sent1, word_flags)
                    
                    # Store mapping for file2
                    file2_to_file1[best_match_idx] = (i, sent1_result['similarity'])
                else:
                    sent1_result['words'] = build_word_array(sent1, [False] * len(words1))
            else:
                # Not plagiarized
                sent1_result['words'] = build_word_array(sent1, [False] * len(words1))

            result['file1'].append(sent1_result)

            if best_match_idx != -1 and best_similarity > 5:
                result['matches'].append({
                    'file1_sentence': i,
                    'file2_sentence': best_match_idx,
                    'similarity': sent1_result['similarity']
                })

        except Exception as e:
            logger.error(f"Error processing file1 sentence {i}: {e}")
            # Fallback: create a default sentence with no highlighting
            result['file1'].append({
                'text': sentences1[i] if i < len(sentences1) else "[Error processing sentence]",
                'words': build_word_array(sentences1[i] if i < len(sentences1) else "", [False]),
                'plagiarized': False,
                'similarity': 0,
                'matched_with': -1
            })

    # ------------------------------------------------------------
    # Process file2 sentences – ALWAYS populate words
    # ------------------------------------------------------------
    for j, sent2 in enumerate(sentences2):
        try:
            words2 = sent2.split()
            sent2_result = {
                'text': sent2,
                'words': [],
                'plagiarized': False,
                'similarity': 0
            }

            # Check if this sentence matches any from file1
            if j in file2_to_file1:
                file1_idx, sim = file2_to_file1[j]
                sent2_result['plagiarized'] = True
                sent2_result['similarity'] = sim

                # Retrieve matching file1 sentence for word-level comparison
                matched_sent1 = sentences1[file1_idx] if file1_idx < len(sentences1) else ""
                match_words1 = {w.lower() for w in matched_sent1.split() if len(w) >= 3}
                word_flags = []
                for word in words2:
                    word_lower = word.lower()
                    is_plag = len(word) >= 3 and sim > 5 and word_lower in match_words1
                    word_flags.append(is_plag)
                sent2_result['words'] = build_word_array(sent2, word_flags)
            else:
                # Unmatched – no plagiarism
                sent2_result['words'] = build_word_array(sent2, [False] * len(words2))

            result['file2'].append(sent2_result)

        except Exception as e:
            logger.error(f"Error processing file2 sentence {j}: {e}")
            # FALLBACK – critical: ensure file2 always has some content
            result['file2'].append({
                'text': sentences2[j] if j < len(sentences2) else "[Error processing sentence]",
                'words': build_word_array(sentences2[j] if j < len(sentences2) else "", [False]),
                'plagiarized': False,
                'similarity': 0
            })

    # Final safety: if result['file2'] is empty for any reason, add the whole text as one sentence
    if not result['file2'] and text2:
        logger.warning("File2 had no sentences after processing – adding full text as fallback")
        result['file2'] = [{
            'text': text2[:500],
            'words': build_word_array(text2[:500], [False]),
            'plagiarized': False,
            'similarity': 0
        }]

    # Log summary
    plag_sent_file1 = sum(1 for s in result['file1'] if s.get('plagiarized', False))
    plag_sent_file2 = sum(1 for s in result['file2'] if s.get('plagiarized', False))
    logger.info(f"✅ Highlighting complete: File1: {plag_sent_file1}/{len(result['file1'])} plagiarized sentences, "
                f"File2: {plag_sent_file2}/{len(result['file2'])} plagiarized sentences")
    
    return result