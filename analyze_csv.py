import pandas as pd
import datetime

import sys

# Wrap execution to write to file
original_stdout = sys.stdout
with open("analysis_results.txt", "w", encoding="utf-8") as f:
    sys.stdout = f
    try:
        # Load the CSV
        file_path = "Planning_Applications.csv"
        try:
            df = pd.read_csv(file_path)
            print(f"Successfully loaded {len(df)} rows.")
        except Exception as e:
            print(f"Error loading CSV: {e}")
            sys.exit()

        # Analyze Dates
        date_cols = ['DATEAPRECV', 'DATE_CREATED', 'DATE_MODIFIED', 'DATEAPVAL']
        print("\n--- Date Analysis ---")
        for col in date_cols:
            if col in df.columns:
                # Attempt to parse dates
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    min_date = df[col].min()
                    max_date = df[col].max()
                    print(f"{col}: Min = {min_date}, Max = {max_date}")
                except Exception as e:
                    print(f"Could not parse {col}: {e}")

        # Analyze Proposals for Home Extensions
        print("\n--- Home Extension Analysis ---")
        # Keywords often associated with home extensions
        keywords = ['single storey', 'side extension', 'rear extension', 'dormer', 'householder', 'conservatory', 'garage conversion', 'two storey']
        pattern = '|'.join(keywords)

        # specific filter for extensions
        extension_df = df[df['PROPOSAL'].str.contains(pattern, case=False, na=False)]
        print(f"Total rows matching extension keywords: {len(extension_df)}")
        print(f"Example proposals:\n{extension_df['PROPOSAL'].head(3).to_string(index=False)}")

        # Analyze Status/Decisions for Extensions
        print("\n--- Decision/Status Analysis (Extensions) ---")
        if 'DECSN' in extension_df.columns:
            print(extension_df['DECSN'].value_counts())
        elif 'DCSTAT' in extension_df.columns:
            print(extension_df['DCSTAT'].value_counts())

        # Check specific columns that might indicate 'Application Type'
        if 'DCAPPTYP' in df.columns:
            print("\n--- Application Types (Top 10) ---")
            print(df['DCAPPTYP'].value_counts().head(10))
            
    finally:
        sys.stdout = original_stdout

# Print confirmation to console
print("Analysis complete. Results written to analysis_results.txt")
