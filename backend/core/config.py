import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
APP_TITLE='ATS RESUME ANALYZER API'
APP_VERSION='1.0.0'
APP_DESCRIPTION='Analyze resume against job description using nlp + ml'
ALLOWED_ORIGINS=[
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173"
]

MAX_FILE_SIZE_MB=5
MAX_FILES_SIZE_BYTES=MAX_FILE_SIZE_MB*1024*1024
SUPPORTED_MIMES_TYPES={
    'application/pdf':'pdf',
    'application/msword':'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'docx'
}
SUPPORTED_EXTENSIONS={'.pdf','.doc','.docx'}
SPACY_MODEL_PRIMARY='en-core-web-nd'
SPACY_MODEL_SECONDARY='en-core-web-sm'
SENTENCE_TRANSFORMER_MODEL=os.getenv("SENTENCE_TRANSFORMER_MODEL","all-MiniLM-L6-v2")

SCORE_WEIGHTS={
    'formatting':20,
    'keywords':25,
    'content':25,
    'skill_validation':15,
    'ats_compatibility':15
}
JD_KEYWORD_WEIGHT=0.6
JD_SEMANTIC_WEIGHT=0.4
    