# JobFindr

A modern job recommendation platform that uses machine learning to match candidates with ideal job opportunities.

## Features

- **Job Recommendations** - AI-powered job matching based on candidate profiles and preferences
- **Resume Parsing** - Intelligent resume analysis to extract skills and experience
- **User Authentication** - Secure OAuth-based authentication
- **Job Applications** - Track and manage job applications
- **Recruiter Dashboard** - Tools for recruiters to post jobs and review candidates
- **Candidate Profiles** - Build and manage professional profiles
- **Career Insights** - ML-driven career recommendations and suggestions

## Tech Stack

- **Backend**: Flask, Flask-SQLAlchemy
- **Machine Learning**: scikit-learn, pandas, numpy
- **Authentication**: Authlib
- **PDF Processing**: pdfminer.six
- **Frontend**: HTML templates with Flask
- **Deployment**: Vercel

## Installation

1. Clone the repository:
```bash
git clone https://github.com/CodeGod25/JobFindr.git
cd JobFindr
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running Locally

```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
jobfindr/
├── api/               # Vercel serverless function entry point
├── app/
│   ├── models.py      # Database models
│   ├── routes/        # Flask route blueprints
│   ├── templates/     # HTML templates
│   ├── ml/            # Machine learning models
│   └── data/          # Data files (jobs, users)
├── run.py            # Development entry point
└── requirements.txt  # Python dependencies
```

## Deployment

This project is configured for deployment on Vercel.

1. Push to GitHub: `git push origin master`
2. Connect to Vercel via GitHub
3. Vercel will automatically deploy on each push

Live deployment: [https://jobfindr-xxx.vercel.app](https://jobfindr-xxx.vercel.app)

## License

MIT License - See LICENSE file for details

## Contact

For questions or feedback, please reach out to the development team.
