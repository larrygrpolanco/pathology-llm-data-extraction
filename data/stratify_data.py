
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_STANDARD_CSV = BASE_DIR / "data" / "gold_standard" / "thyroid_gold_standard.csv"
OUTPUT_DIR = BASE_DIR / "data"

def main():
    if not GOLD_STANDARD_CSV.exists():
        print(f"Error: Gold standard CSV not found at {GOLD_STANDARD_CSV}")
        return

    print("Loading gold standard data...")
    df = pd.read_csv(GOLD_STANDARD_CSV)
    
    # Filter for completel cases
    print(f"Total rows: {len(df)}")
    df_ok = df[df['data_quality_flag'] == 'OK'].copy()
    print(f"Rows with data_quality_flag='OK': {len(df_ok)}")

    # Create stratification key
    # We combine ETE, Margins, Site, and LN Examined Status to ensure balanced splits
    # Handle NaN values by filling with "Unknown" to allow stratification
    
    df_ok['strat_ete'] = df_ok['extrathyroidal_extension'].fillna('Unknown').astype(str)
    df_ok['strat_margins'] = df_ok['margins'].fillna('Unknown').astype(str)
    df_ok['strat_site'] = df_ok['tumor_site'].fillna('Unknown').astype(str)
    df_ok['strat_ln'] = df_ok['lymph_nodes_examined_status'].fillna('Unknown').astype(str)

    # Simplified Site: Right, Left, Bilateral, Isthmus, Other
    def simplify_site(s):
        s = s.lower()
        if 'right' in s and 'left' in s: return 'Bilateral'
        if 'bilateral' in s: return 'Bilateral'
        if 'isthmus' in s: return 'Isthmus'
        if 'right' in s: return 'Right'
        if 'left' in s: return 'Left'
        return 'Other'
    
    df_ok['strat_site_simple'] = df_ok['strat_site'].apply(simplify_site)

    # Create combined key
    df_ok['strata_key'] = (
        df_ok['strat_ete'] + "_" + 
        df_ok['strat_margins'] + "_" + 
        df_ok['strat_site_simple'] + "_" + 
        df_ok['strat_ln']
    )

    # Check for rare classes (single members cannot be split)
    class_counts = df_ok['strata_key'].value_counts()
    singletons = class_counts[class_counts < 2].index.tolist()
    
    # Map singletons to a coarser "Other" strata to prevent error
    if singletons:
        print(f"Warning: {len(singletons)} stratification groups have < 2 samples. Merging them into 'Other_Strat'.")
        df_ok.loc[df_ok['strata_key'].isin(singletons), 'strata_key'] = 'Other_Strat'

    # Split 80/20 (User requested Dev=20%, Test=80%)
    print("Splitting data 20/80 (Dev/Test)...")
    dev_df, test_df = train_test_split(
        df_ok, 
        test_size=0.798, # Approx 80% to get ~325 test vs 82 dev. 407 * 0.8 = 325.6. 
        stratify=df_ok['strata_key'], 
        random_state=42
    )

    print(f"Dev set size: {len(dev_df)}")
    print(f"Test set size: {len(test_df)}")

    # Save
    dev_path = OUTPUT_DIR / "dev_split.csv"
    test_path = OUTPUT_DIR / "test_split.csv"
    
    dev_df.to_csv(dev_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    print(f"Saved {dev_path}")
    print(f"Saved {test_path}")

    # Verify distributions (optional quick check)
    print("\n-- Distribution Check (ETE) --")
    print("Dev:")
    print(dev_df['extrathyroidal_extension'].value_counts(normalize=True).head())
    print("Test:")
    print(test_df['extrathyroidal_extension'].value_counts(normalize=True).head())

if __name__ == "__main__":
    main()
