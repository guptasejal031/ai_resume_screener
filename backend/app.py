from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, render_template, request, redirect, url_for, session
import os
import re   

def extract_structured_data(text):
    skills = [skill for skill in SKILLS_DATABASE if skill in text.lower()]

    experience = 0
    match = re.findall(r'(\d+)\s+years', text.lower())
    if match:
        experience = max(map(int, match))

    return {
        "skills": skills,
        "experience": experience
    }

def extract_name(text):
    lines = text.strip().split("\n")

    for line in lines[:5]:   # check first 5 lines only
        line = line.strip()

        # simple condition: name is short and no numbers
        if len(line.split()) <= 4 and not any(char.isdigit() for char in line):
            return line

    return "Unknown"
from parser import extract_text_from_pdf
from database import init_db, get_connection
from parser import extract_text_from_pdf, extract_experience
from sentence_transformers import SentenceTransformer, util
from flask import send_from_directory

model = SentenceTransformer('all-MiniLM-L6-v2')

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "../resumes"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Make sure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Skill database

SKILLS_DATABASE = [
    "python", "java", "c++", "flask", "django",
    "machine learning", "sql", "mysql",
    "html", "css", "javascript", "react",
    "pandas", "numpy", "tensorflow"
]
# Temporary user storage (for now)



@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )

@app.route("/analyze", methods=["POST"])
def analyze():
    if "username" not in session:
        return redirect(url_for("login"))

    files = request.files.getlist('resumes')

    if not files:
        return "No file uploaded"

    job_description = request.form["job_description"].lower()

    results = []

    for file in files:
        if file.filename == "":
            continue

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        try:
            resume_text_raw = extract_text_from_pdf(file_path)
            resume_text = resume_text_raw.lower()

            # ✅ Extract Name
            candidate_name = extract_name(resume_text_raw)
        except Exception:
            continue

        # STEP 1: Skills
        # ✅ Structured Extraction
        resume_data = extract_structured_data(resume_text)
        jd_data = extract_structured_data(job_description)

        resume_skills = resume_data["skills"]
        jd_skills = jd_data["skills"]

        experience = resume_data["experience"]
        required_experience = jd_data["experience"] if jd_data["experience"] > 0 else 2

        # STEP 3: Matched + Missing Skills
        matched_skills = list(set(resume_skills) & set(jd_skills))
        missing_skills = list(set(jd_skills) - set(resume_skills))
        
        # ✅ NEW: Advanced Job Role Prediction

        predicted_role = "General Role"

        # 🔹 AI / Data Science
        if any(skill in resume_skills for skill in ["machine learning", "tensorflow", "numpy", "pandas"]):
            predicted_role = "AI / Data Science"

        # 🔹 Full Stack
        elif all(skill in resume_skills for skill in ["html", "css", "javascript"]) and \
                any(skill in resume_skills for skill in ["flask", "django"]):
         predicted_role = "Full Stack Developer"

        # 🔹 Frontend
        elif any(skill in resume_skills for skill in ["react", "javascript", "html", "css"]):
            predicted_role = "Frontend Developer"

        # 🔹 Backend
        elif any(skill in resume_skills for skill in ["flask", "django", "java", "python"]):
            predicted_role = "Backend Developer"

        # 🔹 Database
        elif any(skill in resume_skills for skill in ["sql", "mysql"]):
            predicted_role = "Database Developer"

        # 🔹 Cloud / DevOps
        elif any(skill in resume_skills for skill in ["aws", "azure", "cloud", "docker"]):
            predicted_role = "Cloud / DevOps"

        # 🔹 Marketing
        elif any(word in resume_text for word in ["marketing", "seo", "branding", "digital marketing"]):
            predicted_role = "Marketing"

        # 🔹 Sales
        elif any(word in resume_text for word in ["sales", "business development", "client handling"]):
            predicted_role = "Sales"

        # 🔹 Accounting
        elif any(word in resume_text for word in ["accounting", "finance", "tax", "tally"]):
            predicted_role = "Accounting"

        # STEP 4: Rule-Based Score
        if len(jd_skills) == 0:
            skill_score = 0
        else:
            skill_score = len(matched_skills) / len(jd_skills)

        exp_score = min(experience / required_experience, 1) if required_experience else 1

        rule_score = (skill_score * 0.6 + exp_score * 0.4) * 100
         
        def group_by_role(results):
            grouped = {}

            for r in results:
                role = r.get("predicted_role", "Unknown")

                if role not in grouped:
                    grouped[role] = []

                grouped[role].append(r)

            return grouped
        # STEP 5: AI Score (TF-IDF)
        documents = [resume_text, job_description]
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)

        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        ai_score = similarity[0][0] * 100

        # 🔥 BERT Semantic Score
        resume_embedding = model.encode(resume_text, convert_to_tensor=True)
        jd_embedding = model.encode(job_description, convert_to_tensor=True)

        bert_score = util.pytorch_cos_sim(resume_embedding, jd_embedding).item() * 100

                # STEP 6: FINAL SCORE
        explanation = {
            "skill_match": f"{len(matched_skills)} skills matched",
            "experience_match": f"{experience} years experience",
            "tfidf_score": round(ai_score, 2),
            "bert_score": round(bert_score, 2)
        }

        score = (
         rule_score * 0.5 +
         ai_score * 0.2 +
         bert_score * 0.3
        )

        # ✅ NEW: Feedback Generator
        feedback = []

        if experience < required_experience:
            feedback.append("Increase your experience level")

        if len(matched_skills) < 3:
            feedback.append("Add more relevant skills")

        if "project" not in resume_text:
            feedback.append("Include projects section")

        if len(resume_text.split()) < 200:
            feedback.append("Resume content is too short, add more details")

        if not feedback:
            feedback.append("Excellent resume, well aligned with job role")

        # STEP 7: Decision ✅ FIXED
        if score >= 70:
            decision = "Highly Eligible"
        elif score >= 50:
            decision = "Moderately Eligible"
        else:
            decision = "Not Eligible"

        # STEP 8: AI Suggestion (based on score)
        if score >= 70:
            suggestion_text = "Strong match with job requirements."
        elif score >= 50:
            suggestion_text = "Partial match with some missing skills."
        else:
            suggestion_text = "Low match with many missing skills."

        # STEP 9: Skill-based Suggestion (override if needed)
        if missing_skills:
            suggestion_text = "Recommended to learn: " + ", ".join(missing_skills[:3])

        # STEP 10: Save to DB ✅ FIXED (decision added)
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO resumes (user_id, filename, score, decision)
            VALUES (?, ?, ?, ?)
        """, (
            session["user_id"],
            file.filename,
            score,
            decision   # ✅ FIXED
        ))

        conn.commit()
        conn.close()

        # STEP 11: Store result ✅ FIXED
        results.append({
            "filename": file.filename,
            "name": candidate_name, 
            "score": score,
            "decision": decision,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "explanation": explanation,
            "suggestion": suggestion_text,
            "bert_score": int(bert_score),
            "feedback": feedback,
            "predicted_role": predicted_role  
        })
    # STEP 12: Ranking
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    grouped_results = group_by_role(results)

    print("Grouped Results:", grouped_results)
    top_candidates = results[:3]

    usernames = [r["filename"] for r in results]
    scores = [r["score"] for r in results]

    return render_template(
    "result.html",
    results=results,
    grouped_results=grouped_results,
    usernames=usernames,
    scores=scores,
    top_candidates=top_candidates   # ✅ NEW
    )
# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "Username already exists"

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        return "Invalid credentials"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", username=session["username"])

@app.route("/view-resumes")
def view_resumes():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM resumes")
    data = cursor.fetchall()

    conn.close()

    return str([dict(row) for row in data])

# ---------------- RESUME HISTORY ----------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename, score, decision, upload_date
        FROM resumes
        WHERE user_id = ?
        ORDER BY score DESC
    """, (session["user_id"],))

    resumes = cursor.fetchall()
    conn.close()

    # Convert to list and add ranking
    ranked_resumes = []
    rank = 1
    for resume in resumes:
        resume_dict = dict(resume)
        resume_dict["rank"] = rank
        ranked_resumes.append(resume_dict)
        rank += 1

    return render_template("history.html", resumes=ranked_resumes)

@app.route("/delete/<int:resume_id>")
def delete_resume(resume_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    # Delete only user's own resume
    cursor.execute("""
        DELETE FROM resumes 
        WHERE id = ? AND user_id = ?
    """, (resume_id, session["user_id"]))

    conn.commit()
    conn.close()

    return redirect(url_for("history"))
# ---------------- ADMIN PANEL ----------------
# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
def admin():
    if "username" not in session:
        return redirect(url_for("login"))

    # Only allow admin user
    if session["username"] != "admin":
        return "Access Denied"

    conn = get_connection()
    cursor = conn.cursor()

    # 🔍 Get search value from URL
    search = request.args.get("search")

    if search:
        cursor.execute("""
            SELECT resumes.id, users.username, resumes.filename,
                   resumes.score, resumes.decision, resumes.upload_date
            FROM resumes
            JOIN users ON resumes.user_id = users.id
            WHERE users.username LIKE ?
            ORDER BY resumes.score DESC
            """, ('%' + search + '%',))
    else:
        cursor.execute("""
            SELECT resumes.id, users.username, resumes.filename,
               resumes.score, resumes.decision, resumes.upload_date
            FROM resumes
            JOIN users ON resumes.user_id = users.id
            ORDER BY resumes.score DESC
        """)
    data = cursor.fetchall()
    conn.close()

    ranked = []
    rank = 1
    for row in data:
        row_dict = dict(row)
        row_dict["rank"] = rank
        ranked.append(row_dict)
        rank += 1

    # 🔥 ADD ANALYTICS CALCULATIONS HERE
    total_candidates = len(ranked)

    average_score = int(
        sum([r["score"] for r in ranked]) / total_candidates
    ) if total_candidates > 0 else 0

    high_count = len(
        [r for r in ranked if r["decision"] == "Highly Eligible"]
    )

    usernames = [r["username"] for r in ranked]
    scores = [r["score"] for r in ranked]

    return render_template(
        "admin.html",
        resumes=ranked,
        usernames=usernames,
        scores=scores,
        total_candidates=total_candidates,
        average_score=average_score,
        high_count=high_count
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)