import pandas as pd
import os
import sys
from tqdm import tqdm

# Add parent directory to path so we can import from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Job

def run_import(csv_path, limit=500):
    """
    Imports real job data from Kaggle CSV into the SQLite database.
    'limit' controls how many rows to import (Kaggle dataset is huge).
    """
    app = create_app()
    
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        print("Please download the 'Job Description Dataset' from Kaggle and place it at:")
        print(f"{csv_path}")
        return

    print(f"Loading {csv_path}...")
    # Map of Kaggle CSV columns to our expectation
    # Kaggle: 'Job Title', 'Company', 'location', 'Job Description', 'skills'
    try:
        cols = ['Job Title', 'Company', 'location', 'Job Description', 'skills']
        # Reading a sample of the CSV to handle potential encoding issues
        df = pd.read_csv(csv_path, usecols=cols, nrows=limit * 10)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Clean up column names to match our internal logic
    df = df.rename(columns={
        'Job Title': 'Job Title',
        'Company': 'Company Name',
        'location': 'Location',
        'Job Description': 'Job Description',
        'skills': 'Skills'
    })
    
    # Shuffle and pick the limit
    sampled_df = df.sample(n=min(len(df), limit))
    
    with app.app_context():
        print("Initializing database tables...")
        db.create_all()
        
        print(f"Importing {len(sampled_df)} jobs into the database...")
        for _, row in tqdm(sampled_df.iterrows(), total=len(sampled_df)):
            # Convert skills string to list
            skills_raw = str(row['Skills'])
            skills_list = [s.strip() for s in skills_raw.split(',')]
            
            job = Job(
                title=row['Job Title'],
                company=row['Company Name'],
                location=row['Location'],
                description=row['Job Description'],
                # Using the property setter in models.py
                skills=skills_list,
                dept="Engineering", # Defaulting as per schema
                source="Kaggle"
            )
            db.session.add(job)
        
        db.session.commit()
        print("\n[MAGIC COMPLETED] Your database now has real Kaggle job listings!")

if __name__ == "__main__":
    # Standard path based on our previous discussion
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, "job_descriptions.csv")
    run_import(path, limit=500)
