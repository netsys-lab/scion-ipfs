import subprocess
import itertools
import os
import glob
import pandas as pd
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# --- Benchmark Configuration ---
# Define the parameter ranges you want to test
NODE_SIZES = [2000, 5000, 10000]
ATTACKER_FRACTIONS = [0.20, 0.40, 0.60] # Weak, moderate, and strong attacks
SIMULATION_STEPS = 75 # A bit longer for larger networks to stabilize
NUM_RUNS_PER_SCENARIO = 10 # More runs for better statistical confidence

def generate_commands():
    """Generates all command-line commands for the benchmark."""
    commands = []
    # Create the Cartesian product of all parameter lists
    param_combinations = list(itertools.product(NODE_SIZES, ATTACKER_FRACTIONS))
    
    for nodes, attackers in param_combinations:
        cmd = (
            f"python3 run_experiments.py "
            f"--num-nodes {nodes} "
            f"--attacker-fraction {attackers} "
            f"--simulation-steps {SIMULATION_STEPS} "
            f"--num-runs {NUM_RUNS_PER_SCENARIO}"
        )
        commands.append(cmd)
    return commands

def run_command(command):
    """Executes a single command and handles output."""
    try:
        # Using shell=True can be a security risk if commands are from an untrusted source,
        # but here we are generating them ourselves, so it's safe and convenient.
        process = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        return (command, True, process.stdout)
    except subprocess.CalledProcessError as e:
        return (command, False, e.stderr)

def consolidate_results():
    """Finds all individual result CSVs and merges them into one."""
    print("\nConsolidating all result files...")
    # Use the pattern from run_experiments.py to find the files
    pattern = 'results_n*_att*_s*_r*.csv'
    all_files = glob.glob(pattern)
    
    if not all_files:
        print("No result files found to consolidate.")
        return

    df_list = [pd.read_csv(file) for file in all_files]
    combined_df = pd.concat(df_list, ignore_index=True)
    
    master_filename = 'master_results_all_benchmarks.csv'
    combined_df.to_csv(master_filename, index=False)
    print(f"Successfully consolidated {len(all_files)} files into '{master_filename}'")

def main():
    """Main function to orchestrate the benchmark."""
    commands = generate_commands()
    print(f"Generated {len(commands)} unique experiment configurations to run.")
    
    # Use n-1 cores to leave one for system processes
    num_workers = max(1, cpu_count() - 2)
    print(f"Starting parallel execution on {num_workers} cores...")

    with Pool(processes=num_workers) as pool:
        # Use tqdm to create a progress bar for the parallel map
        results = list(tqdm(pool.imap_unordered(run_command, commands), total=len(commands)))

    print("\n--- Benchmark Execution Summary ---")
    success_count = 0
    for command, success, output in results:
        if not success:
            print(f"FAILED: {command}")
            print(f"ERROR: {output}")
        else:
            success_count += 1
    print(f"-----------------------------------")
    print(f"Successfully completed {success_count}/{len(commands)} experiments.")

    # Run the consolidation step
    consolidate_results()

if __name__ == '__main__':
    main()