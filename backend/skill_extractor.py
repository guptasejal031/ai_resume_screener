import spacy
nlp = spacy.load("en_core_web_sm")
import re

# Skill dictionary with normalization
SKILL_MAP = {
    "python": ["python"],
    "java": ["java"],
    "c++": ["c++", "cpp"],
    "javascript": ["javascript", "js"],
    "html": ["html"],
    "css": ["css"],
    "react": ["react", "reactjs"],
    "node.js": ["node", "nodejs", "node.js"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "nlp": ["nlp", "natural language processing"],
    "sql": ["sql"],
    "mongodb": ["mongodb"],
    "data analysis": ["data analysis", "data analytics"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
}

def extract_skills(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)  # clean text

    extracted_skills = set()

    for skill, variations in SKILL_MAP.items():
        for variant in variations:
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, text) or variant in text:
                extracted_skills.add(skill)

    return list(extracted_skills)