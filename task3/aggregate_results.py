import os
import glob
import re
import pandas as pd

def main():
    # Define the output directory and file path
    output_dir = "plots"
    output_file = os.path.join(output_dir, "master_results.csv")

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # File pattern to match the result CSV files in the current directory
    file_pattern = "results_numnodes_*_attfraction_*_steps_*_runs_*.csv"
    csv_files = glob.glob(file_pattern)

    if not csv_files:
        print(f"No CSV files found matching the pattern: {file_pattern}")
        return

    print(f"Found {len(csv_files)} files. Aggregating...")

    df_list = []
    
    # Regex to extract the num_nodes and attacker_fraction from the filename
    # Example: results_numnodes_2000_attfraction_0.2_steps_75_runs_10.csv
    filename_regex = re.compile(r"results_numnodes_(\d+)_attfraction_([0-9\.]+)_steps_\d+_runs_\d+\.csv")

    for file in csv_files:
        # Extract variables from the filename
        match = filename_regex.search(file)
        if match:
            num_nodes = int(match.group(1))
            attacker_fraction = float(match.group(2))
            
            # Read the CSV into a DataFrame
            df = pd.read_csv(file)
            
            # Add the new columns
            df['num_nodes'] = num_nodes
            df['attacker_fraction'] = attacker_fraction
            df['scion_deployment'] = 'random'
            
            df_list.append(df)
        else:
            print(f"Warning: Filename '{file}' did not match the expected extraction regex.")

    if df_list:
        # Concatenate all individual DataFrames into one master DataFrame
        master_df = pd.concat(df_list, ignore_index=True)
        
        # Enforce the specific column order requested
        ordered_cols = [
            'kademlia_strategy', 
            'scion_fraction', 
            'mean_attacker_ratio', 
            'std_dev', 
            'num_nodes', 
            'attacker_fraction', 
            'scion_deployment'
        ]
        master_df = master_df[ordered_cols]
        
        # Save the aggregated data to the target CSV file
        master_df.to_csv(output_file, index=False)
        print(f"Successfully aggregated data into: {output_file}")
        
        # Optional: Print a quick preview
        print("\nPreview of the aggregated data:")
        print(master_df.head())

if __name__ == "__main__":
    main()