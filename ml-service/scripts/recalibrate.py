import sys
import pandas as pd
import json
import os
from sklearn.linear_model import LogisticRegression
import numpy as np

def recalibrate(csv_path, output_path):
    print(f"[RECALIBRATE] Loading data from {csv_path}...")
    
    try:
        df = pd.read_csv(csv_path)
        if df.empty or len(df) < 2:
            print("[ERROR] Insufficient data for recalibration (need at least 2 samples).")
            return

        # Prepare features (raw_score) and target (manual_label)
        X = df[['raw_score']].values
        y = df['label'].values

        # Fit Logistic Regression (Platt Scaling)
        # Note: LogisticRegression fixes the sign such that p = 1 / (1 + exp(-(coef * x + intercept)))
        # In our calibration.py: p = 1 / (1 + exp(A*x + B))
        # Thus: A = -coef, B = -intercept
        clf = LogisticRegression()
        clf.fit(X, y)

        new_a = -float(clf.coef_[0][0])
        new_b = -float(clf.intercept_[0])

        # Save to JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump({'A': new_a, 'B': new_b}, f, indent=4)
        
        print(f"[SUCCESS] Recalibration complete. New constants: A={new_a}, B={new_b}")

    except Exception as e:
        print(f"[ERROR] Recalibration failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python recalibrate.py <csv_path> <output_params_path>")
        sys.exit(1)
    
    recalibrate(sys.argv[1], sys.argv[2])
