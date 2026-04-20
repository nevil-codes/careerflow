# CareerFlow

A Dockerized full-stack web application that helps users track job applications and provides a simple AI-based job match score. Built with Flask and designed to be minimal, functional, and easy to run locally with Docker.

> "I built a Dockerized job tracking system with a simple AI-based job matching feature using Flask. The system supports CRUD operations and is fully containerized for consistent deployment."

## Features

- **Job Tracking** — Add, view, update, and delete job applications
- **Status Management** — Track as Applied, Interview, Rejected, or Offer
- **AI Job Match Score** — Paste a job description and get a 0–100 match score via keyword matching
- **Clean Dashboard** — Simple responsive web UI
- **Dockerized** — Runs in a single container

## Tech Stack

- **Backend:** Python / Flask
- **Frontend:** HTML, CSS, JS (Jinja2 templates)
- **Storage:** In-memory list
- **Container:** Docker

## Project Structure

```
CareerFlow/
├── app.py              # Flask backend with all routes
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container configuration
├── .dockerignore       # Files excluded from Docker build
├── README.md           # Project documentation
└── templates/
    └── index.html      # Dashboard UI (Jinja2 template)
```

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

## Run with Docker

```bash
docker build -t careerflow .
docker run -p 5000:5000 careerflow
```

Open [http://localhost:5000](http://localhost:5000)

## Usage

1. **Add** a job — fill in company, role, and status then click Add
2. **Update** — change the status dropdown and click Update
3. **Delete** — click Delete to remove an entry
4. **Score** — paste a job description and click Calculate Score to see keyword matches

## API Routes

| Method | Route | Description |
|--------|-----------------|-------------------------------|
| GET | `/` | Dashboard |
| POST | `/add` | Add job application |
| GET | `/delete/<id>` | Delete job |
| POST | `/update/<id>` | Update job status |
| POST | `/score` | Get job match score (JSON) |
