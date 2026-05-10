import pdfplumber
import os
import re

def extract_text_from_pdf(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

        return text

    except Exception as e:
        return f"ERROR: Could not read PDF. {str(e)}"


# ✅ NEW: Experience extraction function
def extract_experience(text):
    text = text.lower()
    matches = re.findall(r'(\d+)\s+years', text)

    if matches:
        return max([int(x) for x in matches])

    return 0


if __name__ == "__main__":
    resume_path = "../resumes/sample_resume.pdf"

    if os.path.exists(resume_path):
        content = extract_text_from_pdf(resume_path)

        print("\n✅ Resume Text Extracted:\n")
        print(content)

        # ✅ NEW: Show extracted experience
        experience = extract_experience(content)
        print(f"\n📊 Experience Detected: {experience} years")

    else:
        print("❌ Resume file not found!")


from docx import Document

def extract_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        text = ""

        for para in doc.paragraphs:
            text += para.text + "\n"

        return text

    except Exception as e:
        return f"ERROR: Could not read DOCX. {str(e)}"