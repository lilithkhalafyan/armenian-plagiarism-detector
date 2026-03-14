"""AI-generated text detection utilities."""

import re

from config import AI_PATTERNS, logger


def detect_ai_content(text: str, detailed: bool = False) -> dict:
    """Detect if text is AI-generated using pattern matching."""
    if not text or len(text) < 200:
        return {
            'ai_percentage': 0,
            'is_ai_generated': False,
            'confidence': 0,
            'features': {},
            'sentences': []
        }

    text_lower = text.lower()
    words = text_lower.split()

    if len(words) < 50:
        return {
            'ai_percentage': 0,
            'is_ai_generated': False,
            'confidence': 0,
            'features': {},
            'sentences': []
        }

    # Get patterns from JSON
    ai_phrases = AI_PATTERNS.get('ai_phrases', [])
    overused_words = AI_PATTERNS.get('overused_words', [])
    formal_words = AI_PATTERNS.get('formal_words', [])
    explanatory = AI_PATTERNS.get('explanatory_phrases', [])
    transitions = AI_PATTERNS.get('transition_words', [])

    # Count patterns
    ai_phrase_count = 0
    ai_phrases_found = []
    for phrase in ai_phrases:
        if phrase in text_lower:
            ai_phrase_count += 1
            ai_phrases_found.append(phrase)

    overused_count = 0
    for word in overused_words:
        count = text_lower.count(' ' + word + ' ')
        if count > 0:
            overused_count += count

    formal_count = 0
    for word in formal_words:
        count = text_lower.count(word)
        if count > 0:
            formal_count += count

    explanatory_count = 0
    for phrase in explanatory:
        if phrase in text_lower:
            explanatory_count += 1

    transition_count = 0
    for word in transitions:
        count = text_lower.count(' ' + word + ' ')
        if count > 0:
            transition_count += count

    # Sentence analysis
    sentences = re.split(r'[.!?…]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    starter_repetition = 0
    if len(sentences) >= 5:
        starters = []
        for sent in sentences:
            first_words = sent.split()[:2]
            if first_words:
                starter = ' '.join(first_words).lower()
                starters.append(starter)

        if starters:
            unique_starters = len(set(starters))
            starter_repetition = 1 - (unique_starters / len(starters))

    # Calculate score
    total_score = 0
    total_sentences = 0

    sentence_scores_list = []
    for sent in sentences:
        sent_lower = sent.lower()
        sent_score = 0

        for phrase in ai_phrases:
            if phrase in sent_lower:
                sent_score += 50
                break

        for word in overused_words:
            if ' ' + word + ' ' in sent_lower:
                sent_score += 10

        for word in formal_words:
            if word in sent_lower:
                sent_score += 5

        for phrase in explanatory:
            if phrase in sent_lower:
                sent_score += 10
                break

        sent_score = min(100, sent_score)
        sentence_scores_list.append(sent_score)
        total_score += sent_score
        total_sentences += 1

    # Calculate average score
    if total_sentences > 0:
        ai_score = total_score / total_sentences
    else:
        ai_score = 0

    # Round to integer for JSON serialization
    ai_score_int = int(round(ai_score))

    # Sentence-level details
    sentence_scores = []
    if detailed:
        for i, sent in enumerate(sentences[:20]):
            sent_score = sentence_scores_list[i] if i < len(sentence_scores_list) else 0
            sentence_scores.append({
                'text': sent,
                'ai_score': int(sent_score),
                'is_ai': sent_score > 40
            })

    # Features as Python native types
    features = {
        'ai_phrases_found': int(ai_phrase_count),
        'overused_words_count': int(overused_count),
        'formal_words_count': int(formal_count),
        'explanatory_count': int(explanatory_count),
        'transition_count': int(transition_count),
        'starter_repetition': float(round(starter_repetition, 2)),
        'sentences_analyzed': int(total_sentences)
    }

    result = {
        'ai_percentage': ai_score_int,
        'is_ai_generated': bool(ai_score_int > 55),
        'confidence': float(round(ai_score_int / 100, 2)),
        'features': features
    }

    if detailed:
        result['sentences'] = sentence_scores
        result['sentence_count'] = int(len(sentences))
        if ai_phrases_found:
            result['matching_phrases'] = ai_phrases_found[:5]
    else:
        result['sentences'] = []

    return result
