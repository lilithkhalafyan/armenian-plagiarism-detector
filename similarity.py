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
    """Create word-level highlighting for comparison."""

    # Clean texts
    text1 = re.sub(r'\s+', ' ', text1).strip()
    text2 = re.sub(r'\s+', ' ', text2).strip()

    # Split into sentences
    sentences1 = re.split(r'[.!?…]+', text1)
    sentences2 = re.split(r'[.!?…]+', text2)

    sentences1 = [s.strip() for s in sentences1 if len(s.strip()) > 5]
    sentences2 = [s.strip() for s in sentences2 if len(s.strip()) > 5]

    # If no sentences, treat whole text as one sentence
    if not sentences1 and text1:
        sentences1 = [text1]
    if not sentences2 and text2:
        sentences2 = [text2]

    result = {
        'file1': [],
        'file2': [],
        'matches': []
    }

    logger.info(f"📊 Highlighting: {len(sentences1)} sentences in file1, {len(sentences2)} in file2")

    # Process file1 sentences
    for i, sent1 in enumerate(sentences1):
        try:
            words1 = sent1.split()
            sent_result = {
                'text': sent1,
                'words': [],
                'plagiarized': False,
                'similarity': 0,
                'matched_with': -1
            }

            best_match_idx = -1
            best_similarity = 0

            # Find best matching sentence in file2
            for j, sent2 in enumerate(sentences2):
                words2 = sent2.split()

                if words1 and words2:
                    similarity = calculate_basic_similarity(sent1, sent2)
                else:
                    similarity = 0

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = j

            # Lower threshold to catch plagiarism
            if best_similarity > 15:  # Threshold at 15%
                sent_result['plagiarized'] = True
                sent_result['similarity'] = round(float(best_similarity), 1)
                sent_result['matched_with'] = best_match_idx

                # Mark individual words as plagiarized
                if best_match_idx >= 0 and best_match_idx < len(sentences2):
                    match_sent = sentences2[best_match_idx]
                    match_words = set(match_sent.split())
                    for word in words1:
                        sent_result['words'].append({
                            'text': word,
                            'plagiarized': word in match_words
                        })

                    result['matches'].append({
                        'file1_sentence': i,
                        'file2_sentence': best_match_idx,
                        'similarity': sent_result['similarity']
                    })
                else:
                    for word in words1:
                        sent_result['words'].append({'text': word, 'plagiarized': False})
            else:
                # Not plagiarized
                for word in words1:
                    sent_result['words'].append({'text': word, 'plagiarized': False})

            result['file1'].append(sent_result)

        except Exception as e:
            logger.warning(f"Error processing file1 sentence {i}: {e}")
            words = sent1.split() if sent1 else []
            result['file1'].append({
                'text': sent1[:100] + "..." if sent1 else "",
                'words': [{'text': w, 'plagiarized': False} for w in words[:10]],
                'plagiarized': False,
                'similarity': 0
            })

    # Process file2 sentences
    for j, sent2 in enumerate(sentences2):
        try:
            words2 = sent2.split()
            sent_result = {
                'text': sent2,
                'words': [],
                'plagiarized': False,
                'similarity': 0
            }

            # Check if this sentence matches any in file1
            matched = False
            for match in result['matches']:
                if match['file2_sentence'] == j:
                    matched = True
                    sent_result['plagiarized'] = True
                    sent_result['similarity'] = match['similarity']
                    break

            if not matched:
                for word in words2:
                    sent_result['words'].append({'text': word, 'plagiarized': False})

            result['file2'].append(sent_result)

        except Exception as e:
            logger.warning(f"Error processing file2 sentence {j}: {e}")
            words = sent2.split() if sent2 else []
            result['file2'].append({
                'text': sent2[:100] + "..." if sent2 else "",
                'words': [{'text': w, 'plagiarized': False} for w in words[:10]],
                'plagiarized': False,
                'similarity': 0
            })

    # Log results
    total_plagiarized = sum(1 for s in result['file1'] if s['plagiarized'])
    total_words_plagiarized = 0
    for sent in result['file1']:
        if sent.get('plagiarized'):
            for word in sent.get('words', []):
                if word.get('plagiarized'):
                    total_words_plagiarized += 1

    logger.info(f"✅ Highlighting complete: {total_plagiarized} plagiarized sentences, {total_words_plagiarized} plagiarized words")

    return result
