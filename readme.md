# ATS Resume Analyzer – AI-Powered Resume Intelligence Platform

An AI-powered ATS (Applicant Tracking System) Resume Analyzer built using FastAPI, NLP, Sentence Transformers, and Groq LLMs. The platform evaluates resumes, validates claimed skills against project and experience descriptions, compares resumes with job descriptions, calculates ATS scores, and generates personalized feedback.

**Its key innovation is an AI-powered Project Recommendation Engine that identifies skill gaps and suggests relevant, practical projects candidates can build to strengthen their resumes and improve their chances of getting shortlisted.**

---

## Features

### 1. Resume Parsing
- Supports PDF and DOCX resumes.
- Extracts raw text from uploaded files.
- Handles multiple resume formats.
- Identifies important resume sections.

### 2. AI-Powered Resume Analysis

Automatically extracts and analyzes:
- Technical and soft skills.
- Work experience.
- Projects.
- Education.
- Relevant keywords.
- Action verbs.
- Contact information.

### 3. ATS Scoring Engine

Calculates an overall ATS score based on:
- Formatting quality.
- Keyword optimization.
- Content quality.
- ATS compatibility.
- Skill validation.

Provides individual component scores to help candidates understand their resume performance.

### 4. Intelligent Skill Validation

Validates whether the skills mentioned in a resume are supported by actual project descriptions and work experience.

**Example:**

Claimed Skill:
- Docker

Project Evidence:
- Not Found

Result:
- Unvalidated Skill

This helps identify skills that are listed but not sufficiently demonstrated through practical experience.

### 5. Job Description Matching

Compares resumes with specific job descriptions using:
- Sentence Transformers.
- Semantic similarity.
- Keyword matching.

Provides:
- Resume–Job Match Percentage.
- Matched Keywords.
- Missing Keywords.
- Skills Gap Analysis.
- Job-specific improvement recommendations.

### 6. AI-Powered Project Recommendation Engine (Key Innovation)

An intelligent recommendation system that suggests relevant projects candidates can build to improve their resumes based on their existing skills, missing skills, career interests, and target job descriptions.

**How it works:**
1. Analyzes the candidate's existing technical skills and projects.
2. Identifies missing skills by comparing the resume with the target job description.
3. Detects areas where practical project experience is insufficient.
4. Uses Groq LLMs to generate personalized project recommendations.
5. Suggests projects that help candidates demonstrate missing technical skills.

**Each project recommendation includes:**
- Project Title.
- Project Description.
- Technologies and Tools Required.
- Skills Covered.
- Key Features to Implement.
- Difficulty Level (Beginner, Intermediate, Advanced).
- Expected Resume Impact.
- Why the Project Is Relevant to the Target Job.

**Example:**

Target Role: Backend Developer

Missing Skills:
- Redis
- Docker
- CI/CD

AI-Generated Project Suggestion:

**Project: Scalable Task Management API**

Suggested Technologies:
- Python
- FastAPI
- PostgreSQL
- Redis
- Docker
- GitHub Actions

Key Features:
- JWT Authentication.
- REST API Development.
- Redis Caching.
- Database Integration.
- Docker Containerization.
- CI/CD Pipeline.

Expected Outcome:

A practical project that demonstrates backend development, caching, containerization, and deployment skills relevant to backend engineering roles.

**The goal is not just to tell candidates what is missing from their resumes, but to guide them on how to acquire and demonstrate those skills through real projects.**

### 7. Detailed AI Feedback Engine

Generates personalized resume improvement recommendations, including:
- Resume Strengths.
- Weaknesses.
- Improvement Suggestions.
- ATS Optimization Recommendations.
- Missing Skills.
- Content Enhancement Suggestions.

### 8. Professional PDF Report Generation

Generates downloadable PDF reports containing:
- Overall ATS Score.
- Component-wise Scores.
- Skill Validation Results.
- Job Description Match Analysis.
- Matched and Missing Keywords.
- Detailed AI Feedback.
- Project Recommendations.

### 9. User History Management

Uses Supabase to store and manage previous resume analyses.

Features:
- View Previous Analyses.
- Access Saved Results.
- Track Resume Improvements.
- Delete Previous Analysis Records.

### 10. Secure Authentication
- JWT-based authentication.
- Protected API endpoints.
- User-specific analysis history.

---

## Tech Stack

### Backend
- Python
- FastAPI
- REST APIs

### AI / NLP
- Groq LLM
- spaCy
- Sentence Transformers
- Semantic Similarity
- Cosine Similarity
- NLP-based Skill Extraction

### Database
- Supabase

### Authentication
- JWT Authentication

### PDF Generation
- WeasyPrint

### Development Tools
- Git
- GitHub
- Uvicorn
- Swagger UI

---

## Project Architecture

```text
                    User
                      |
                      v
                FastAPI API
                      |
                      v
                Resume Parser
                      |
                      v
               Groq Resume Parser
                      |
                      v
              Resume Data Extraction
                      |
          +-----------+-----------+
          |                       |
          v                       v
    Skill Validation          ATS Scoring
          |                       |
          +-----------+-----------+
                      |
                      v
               JD Matcher
                      |
                      v
                Skills Gap
                   Analysis
                      |
          +-----------+-----------+
          |                       |
          v                       v
     Feedback Engine      Project Recommendation
                                  Engine
          |                       |
          +-----------+-----------+
                      |
                      v
                Supabase Storage
                      |
                      v
              PDF Report Generator
                      |
                      v
                 Final Report
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/analyze-resume` | Uploads and analyzes a resume |
| GET | `/api/v1/health` | Checks API and model status |
| GET | `/api/v1/history` | Retrieves previous analyses |
| DELETE | `/api/v1/history/{analysis_id}` | Deletes an analysis record |
| POST | `/api/v1/generate-pdf` | Generates a downloadable PDF report |

---

## Installation and Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ats-resume-analyzer.git
cd ats-resume-analyzer
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file and configure the required credentials:

```env
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
JWT_SECRET_KEY=your_secret_key
```

### 6. Run Application

```bash
uvicorn backend.main:app --reload
```

Application URL:

```text
http://localhost:8000
```

Swagger API Documentation:

```text
http://localhost:8000/docs
```

---

## Application Workflow

1. User uploads a PDF or DOCX resume.
2. Resume text is extracted.
3. Groq LLM parses and structures resume information.
4. Skills are validated against projects and experience.
5. ATS scoring engine calculates the resume score.
6. Resume is compared with the target job description.
7. Missing keywords and skill gaps are identified.
8. AI feedback engine generates improvement suggestions.
9. Project Recommendation Engine suggests practical projects based on identified skill gaps.
10. Analysis results are stored in Supabase.
11. A professional PDF report is generated.

---

## Key Innovations

- **Evidence-Based Skill Validation:** Evaluates whether claimed skills are supported by practical project or experience evidence.
- **Semantic Job Matching:** Uses transformer-based embeddings to identify contextual similarity between resumes and job descriptions.
- **Intelligent Project Recommendations:** Converts identified skill gaps into actionable project ideas tailored to target job roles.
- **Personalized Resume Improvement:** Combines ATS scoring, skill analysis, and AI-generated feedback into one platform.
- **End-to-End Resume Intelligence:** Helps candidates understand their current resume quality and plan concrete improvements.

---

## Future Improvements

- AI-Based Resume Rewriting.
- Grammar and Spelling Checker.
- Multi-Language Resume Support.
- Personalized Learning Roadmaps.
- Resume Ranking System.
- Batch Resume Analysis.
- Recruiter Dashboard.
- GitHub Project Verification.
- AI-Powered Interview Preparation.
- Project Implementation Roadmaps.

---

## Learning Outcomes

This project demonstrates practical experience with:

- Backend Development using FastAPI.
- REST API Design and Development.
- NLP Pipelines and Information Extraction.
- Sentence Embeddings and Semantic Search.
- Cosine Similarity.
- LLM Integration using Groq.
- AI-Based Recommendation Systems.
- Skill Gap Analysis.
- JWT Authentication.
- Supabase Database Integration.
- PDF Report Generation.
- Modular Software Architecture.

---

## Author

**Vanshika Dhull**

Built as an AI-powered Resume Intelligence Platform that goes beyond traditional ATS scoring by helping candidates identify skill gaps, improve their resumes, and discover practical projects aligned with their target career paths.
