import argparse
import pandas as pd
from tqdm import tqdm
from simulation import SybilSimulation

# --- Experiment Configuration ---
SCION_FRACTIONS_TO_TEST = [0.0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20]
KADEMLIA_STRATEGIES_TO_TEST = ['default', 'prefer_scion']

def parse_args():
    parser = argparse.ArgumentParser(description="Run IPFS/SCION Sybil Attack Simulation Experiments")
    parser.add_argument('--num-nodes', type=int, default=1000, help='Number of nodes in the simulation')
    parser.add_argument('--attacker-fraction', type=float, default=0.40, help='Fraction of attacker nodes')
    parser.add_argument('--simulation-steps', type=int, default=50, help='Number of simulation steps')
    parser.add_argument('--num-runs-per-scenario', type=int, default=5, help='Number of runs per scenario')
    return parser.parse_args()

def main():
    args = parse_args()
    NUM_NODES = args.num_nodes
    ATTACKER_FRACTION = args.attacker_fraction
    SIMULATION_STEPS = args.simulation_steps
    NUM_RUNS_PER_SCENARIO = args.num_runs_per_scenario

    print("Starting IPFS/SCION Sybil Attack Simulation Experiments")
    
    results = []

    for strategy in tqdm(KADEMLIA_STRATEGIES_TO_TEST, desc="Testing Strategies"):
        for scion_fraction in tqdm(SCION_FRACTIONS_TO_TEST, desc=f"Strategy: {strategy}", leave=False):
            run_results = []
            for i in range(NUM_RUNS_PER_SCENARIO):
                sim = SybilSimulation(
                    num_nodes=NUM_NODES,
                    attacker_fraction=ATTACKER_FRACTION,
                    scion_fraction=scion_fraction,
                    scion_deployment_strategy='random',
                    kademlia_strategy=strategy
                )
                sim.run(SIMULATION_STEPS)
                final_attacker_ratio = sim.analyze_results()
                run_results.append(final_attacker_ratio)
            
            mean_ratio = pd.Series(run_results).mean()
            std_dev = pd.Series(run_results).std()
            
            results.append({
                'kademlia_strategy': strategy,
                'scion_fraction': scion_fraction,
                'mean_attacker_ratio': mean_ratio,
                'std_dev': std_dev
            })

    results_df = pd.DataFrame(results)
    output_filename = f'results_numnodes_{NUM_NODES}_attfraction_{ATTACKER_FRACTION}_steps_{SIMULATION_STEPS}_runs_{NUM_RUNS_PER_SCENARIO}.csv'
    results_df.to_csv(output_filename, index=False)
    print(f"\nExperiment complete. Results saved to {output_filename}")
    print(results_df)

if __name__ == '__main__':
    main()