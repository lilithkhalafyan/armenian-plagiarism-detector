"""Configuration and shared data for the plagiarism detector."""

import os
import json
import logging
import secrets

# ==================================================
# LOGGING CONFIGURATION
# ==================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('plagiarism_detector.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('plagiarism_detector')

# ==================================================
# PATHS / FILES
# ==================================================
UPLOAD_FOLDER = 'uploads'
DB_PATH = 'plagiarism.db'
SYNONYMS_FILE = 'armenian_synonyms.json'
THEME_KEYWORDS_FILE = 'theme_keywords.json'
STOPWORDS_FILE = 'armenian_stopwords.json'
AI_PATTERNS_FILE = 'armenian_ai_patterns.json'

# ==================================================
# DEFAULTS
# ==================================================
DEFAULT_SYNONYMS = {
    'համակարգ': ['համակարգ', 'սիստեմ', 'կառուցվածք'],
    'տվյալ': ['տվյալ', 'ինֆորմացիա', 'դատա'],
    'ծրագիր': ['ծրագիր', 'պրոգրամ', 'կոդ'],
    'օգտագործող': ['օգտագործող', 'յուզեր', 'մարդ'],
    'արխիվ': ['արխիվ', 'ֆայլ', 'փաստաթուղթ'],
}

DEFAULT_THEMES = {
    'անվտանգություն': ['անվտանգություն', 'պաշտպանություն', 'հաքեր', 'կրիպտո', 'գաղտնագրություն'],
    'ծրագրավորում': ['ծրագրավորում', 'կոդ', 'ալգորիթմ', 'python', 'javascript', 'ծրագիր'],
    'տվյալների բազա': ['տվյալ', 'բազա', 'sql', 'mysql', 'postgresql', 'տվյալների'],
    'արհեստական բանականություն': ['արհեստական', 'բանականություն', 'մեքենա', 'սովորում', 'ai', 'մլ'],
    'ցանցեր': ['ցանց', 'ինտերնետ', 'պրոտոկոլ', 'tcp/ip', 'http', 'համացանց'],
}

DEFAULT_STOPWORDS = {
    'stopwords': [
        'և', 'է', 'էր', 'որ', 'չէ', 'այն', 'դա', 'նա', 'մենք', 'դուք',
        'նրանք', 'համար', 'մասին', 'հետ', 'առանց', 'կամ', 'բայց',
        'եթե', 'ուրեմն', 'սակայն', 'մի', 'ոչ', 'այո', 'շատ', 'քիչ'
    ]
}

DEFAULT_AI_PATTERNS = {
    'ai_phrases': [
        "որպես արհեստական բանականություն",
        "ես արհեստական բանականություն եմ",
        "ես ձեզ կօգնեմ",
        "ինչպես կարող եմ օգնել",
        "ինձ հայտնի չէ",
        "իմ գիտելիքները թարմացվել են",
        "ըստ իմ տվյալների",
        "ինչպես արդեն նշեցի"
    ],
    'overused_words': [
        "կարևոր", "անհրաժեշտ", "պետք", "հարկ", "ակնհայտ",
        "միանշանակ", "անկասկած", "իրականում", "ըստ էության"
    ],
    'formal_words': [
        "ողջունում", "հարգելի", "հարգանքներով", "խնդրում", "շնորհակալություն"
    ],
    'explanatory_phrases': [
        "այսինքն", "այլ կերպ ասած", "նշանակում է", "ուրեմն"
    ],
    'transition_words': [
        "սակայն", "բայց", "քանի որ", "որովհետև", "հետևաբար"
    ]
}

# ==================================================
# UTILS
# ==================================================

def load_json_file(filename: str, default: dict = None) -> dict:
    """Load JSON file with error handling."""
    if default is None:
        default = {}

    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"✅ Successfully loaded {filename}")
                return data
        else:
            logger.warning(f"⚠️ File {filename} not found, creating default")
            save_json_file(filename, default)
            return default
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing {filename}: {e}")
        return default
    except Exception as e:
        logger.error(f"❌ Error loading {filename}: {e}")
        return default


def save_json_file(filename: str, data: dict) -> bool:
    """Save JSON file safely."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Successfully saved {filename}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving {filename}: {e}")
        return False


# ==================================================
# DATA LOADING
# ==================================================
# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logger.info("📁 Loading configuration files...")

SYNONYMS = load_json_file(SYNONYMS_FILE, DEFAULT_SYNONYMS)
if not SYNONYMS:
    SYNONYMS = DEFAULT_SYNONYMS
    save_json_file(SYNONYMS_FILE, SYNONYMS)

THEME_KEYWORDS = load_json_file(THEME_KEYWORDS_FILE, DEFAULT_THEMES)
if not THEME_KEYWORDS:
    THEME_KEYWORDS = DEFAULT_THEMES
    save_json_file(THEME_KEYWORDS_FILE, THEME_KEYWORDS)

stopwords_data = load_json_file(STOPWORDS_FILE, DEFAULT_STOPWORDS)
STOPWORDS = stopwords_data.get('stopwords', DEFAULT_STOPWORDS['stopwords'])
if not STOPWORDS:
    STOPWORDS = DEFAULT_STOPWORDS['stopwords']
    save_json_file(STOPWORDS_FILE, {'stopwords': STOPWORDS})

AI_PATTERNS = load_json_file(AI_PATTERNS_FILE, DEFAULT_AI_PATTERNS)
if not AI_PATTERNS:
    AI_PATTERNS = DEFAULT_AI_PATTERNS
    save_json_file(AI_PATTERNS_FILE, AI_PATTERNS)

# ==================================================
# SEMANTIC MODEL
# ==================================================
try:
    from sentence_transformers import SentenceTransformer
    MODEL_AVAILABLE = True
    logger.info("✅ SentenceTransformer loaded successfully")
except ImportError:
    MODEL_AVAILABLE = False
    logger.warning("⚠️ SentenceTransformer not available, using TF-IDF only")

SEMANTIC_MODEL = None
if MODEL_AVAILABLE:
    try:
        logger.info("🔄 Loading sentence transformer model...")
        SEMANTIC_MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("✅ Semantic model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Could not load semantic model: {e}")
        SEMANTIC_MODEL = None
