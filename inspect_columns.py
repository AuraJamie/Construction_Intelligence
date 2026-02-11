import pandas as pd
import sys

# Wrap output
original_stdout = sys.stdout
with open("columns_info.txt", "w", encoding="utf-8") as f:
    sys.stdout = f
    try:
        df = pd.read_csv("Planning_Applications.csv")
        print("Columns:", df.columns.tolist())
        print("\nFirst row sample:")
        print(df.iloc[0].to_dict())
        
        # Check for empty DECSN
        print("\nNull DECSN count:", df['DECSN'].isna().sum())
        
    except Exception as e:
        print(e)
    finally:
        sys.stdout = original_stdout
