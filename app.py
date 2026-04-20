from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

jobs = []
next_id = 1

KEYWORDS = ["python", "java", "docker", "aws", "sql", "flask"]


def compute_job_score(text):
    """Return a match score 0-100 based on keyword hits."""
    text_lower = text.lower()
    matches = [kw for kw in KEYWORDS if kw in text_lower]
    return min(int((len(matches) / len(KEYWORDS)) * 100), 100), matches


@app.route("/")
def dashboard():
    return render_template("index.html", jobs=jobs)


@app.route("/add", methods=["POST"])
def add_job():
    global next_id
    company = request.form.get("company", "").strip()
    role = request.form.get("role", "").strip()
    status = request.form.get("status", "Applied")
    if company and role:
        jobs.append({"id": next_id, "company": company, "role": role, "status": status})
        next_id += 1
    return redirect(url_for("dashboard"))


@app.route("/delete/<int:job_id>")
def delete_job(job_id):
    global jobs
    jobs = [j for j in jobs if j["id"] != job_id]
    return redirect(url_for("dashboard"))


@app.route("/update/<int:job_id>", methods=["POST"])
def update_job(job_id):
    new_status = request.form.get("status", "")
    for job in jobs:
        if job["id"] == job_id:
            job["status"] = new_status
            break
    return redirect(url_for("dashboard"))


@app.route("/score", methods=["POST"])
def score():
    description = request.form.get("description", "")
    if not description.strip():
        return jsonify({"score": 0, "matched": []})
    value, matched = compute_job_score(description)
    return jsonify({"score": value, "matched": matched})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
