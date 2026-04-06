# Validation Test for Real Data
# ------------------------------
# Run this once you have imported some Kaggle jobs.

import os
import sys
import pandas as pd

# Set up path to project
PROJECT_ROOT = os.path.abspath(os.curdir)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from app import create_app, db
from app.models import Job, User
from app.ml.recommender import JobRecommender

app = create_app()

with app.app_context():
    # 1. Total Job Count
    total_jobs = Job.query.count()
    print(f"Total jobs in DB: {total_jobs}")
    
    if total_jobs == 0:
        print("ALERT: Database is empty. Please run 'python data_ingestion/import_kaggle.py' first.")
    else:
        # 2. Recommender Initialization
        recommender = JobRecommender()
        print(f"Recommender indexed {len(recommender.jobs)} jobs.")
        
        # 3. Test a typical "Real World" Query
        test_query = "Senior Python Developer with AWS and Docker experience"
        print(f"\nTesting recommendation for query: '{test_query}'")
        
        recommendations = recommender.recommend(test_query, top_n=5)
        
        if not recommendations:
            print("No recommendations found.")
        else:
            print(f"Found {len(recommendations)} matches:")
            results = []
            for r in recommendations:
                # The recommender uses 'match_score' for the percentage display
                score = r.get('match_score', 0)
                results.append({
                    "Score %": f"{score}%",
                    "Title": r.get('title', 'Unknown'),
                    "Company": r.get('company', 'Unknown'),
                    "Location": r.get('location', 'N/A'),
                    "Match Reason": r.get('match_reason', 'N/A')
                })
            
            # Display as table
            df_results = pd.DataFrame(results)
            print(df_results.to_string(index=False))
