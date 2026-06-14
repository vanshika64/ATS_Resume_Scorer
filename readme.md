# ATS Resume Analyzer

An AI-powered ATS (Applicant Tracking System) Resume Analyzer built using FastAPI, NLP, Sentence Transformers, and Groq LLMs. The application evaluates resumes, validates skills against projects, compares resumes with job descriptions, calculates ATS scores, generates detailed feedback, and exports professional PDF reports.

---

## Features

### Resume Parsing
* Supports PDF and DOCX resumes
* Extracts raw text from uploaded files
* Handles multiple resume formats
### AI-Powered Resume Analysis

* Extracts:

  * Skills
  * Experience
  * Projects
  * Education
  * Keywords
  * Action Verbs
  * Contact Information

### ATS Scoring

Calculates an overall ATS score based on:

* Formatting quality
* Keyword optimization
* Content quality
* ATS compatibility
* Skill validation

### Skill Validation

Validates whether claimed skills are supported by:

* Projects
* Experience descriptions

Example:

Skill Listed:

* Docker

Project Evidence:

* Not Found

Result:

* Unvalidated Skill

### Job Description Matching

Compares resumes with job descriptions using:

* Semantic Similarity
* Keyword Matching

Provides:
* Match Percentage
* Missing Keywords
* Matched Keywords
* Skills Gap Analysis

### Detailed Feedback Engine

Generates:

* Strengths
* Weaknesses
* Improvement Suggestions
* ATS Optimization Recommendations

### PDF Report Generation

Creates professional PDF reports containing:

* ATS Score
* Component Scores
* Skill Validation Results
* JD Match Analysis
* Detailed Feedback

### User History

Stores previous analyses using Supabase.
---

## Tech Stack

### Backend

* FastAPI
* Python

### AI / NLP

* spaCy
* Sentence Transformers
* Groq LLM

### Database

* Supabase

### PDF Generation

* WeasyPrint

### Authentication

* JWT Authentication

---

## Project Architecture

```text
User
 ↓
FastAPI API
 ↓
Resume Parser
 ↓
Groq Resume Parser
 ↓
Skill Validation
 ↓
ATS Scoring Engine
 ↓
JD Matcher
 ↓
Feedback Engine
 ↓
Supabase Storage
 ↓
PDF Report Generator
 ↓
Response
```

---

## API Endpoints

### Analyze Resume

```http
POST /api/v1/analyze-resume
```

Uploads a resume and generates ATS analysis.

---

Checks API and model status.

---

### Get User History

```http
GET /api/v1/history
```

Returns previously analyzed resumes.

---

### Delete Analysis

```http
DELETE /api/v1/history/{analysis_id}
```

Deletes a stored analysis record.

---

### Generate PDF

```http
POST /api/v1/generate-pdf
```

Generates a downloadable PDF report.

---

## Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/ats-resume-analyzer.git
cd ats-resume-analyzer
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux / Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
uvicorn backend.main:app --reload
```

Application will run at:

```text
http://localhost:8000
```

Swagger Documentation:

```text
http://localhost:8000/docs
```
## Future Improvements

* Grammar Checking
* Resume Section Recommendations
* Multi-Language Resume Support
* AI Resume Rewriting Suggestions
* Resume Ranking System
* Batch Resume Analysis
* Recruiter Dashboard

---

## Learning Outcomes

This project demonstrates practical experience with:

* FastAPI Backend Development
* REST API Design
* NLP Pipelines
* Semantic Search
* Embedding Models
* Cosine Similarity
* ATS Systems
* LLM Integration
* Authentication
* Database Integration
* PDF Generation
* Software Architecture

---

## Author

Vanshika Dhull

Built as a full-stack AI-powered ATS Resume Analysis platform for helping candidates optimize resumes for Applicant Tracking Systems.
