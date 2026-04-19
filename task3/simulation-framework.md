# IPFS over SCION: Sybil Attack Simulation Framework and Results

## 1. Simulation Framework Overview
The simulation framework is a custom discrete-time event simulator designed to evaluate the effectiveness of SCION-based peer validation in mitigating Sybil (eclipse) attacks within an IPFS-like Kademlia Distributed Hash Table (DHT). 

It models a decentralized network experiencing routing table poisoning, comparing conventional network behaviors against SCION-enabled trust mechanisms. The framework is composed of three main Python modules: the core simulator (`simulation.py`), the experiment runner (`run_experiments.py`), and the parallelized benchmarking suite (`benchmark.py`).

### 1.1 Network Topology & Node Roles
The network topology is generated using the **Barabási-Albert (BA) model** to accurately reflect the scale-free, power-law degree distributions typical of real-world peer-to-peer systems like IPFS. The framework scales up to 10,000 nodes, divided into three specific roles:
*   **Honest Peer:** A legitimate network participant that follows the DHT protocol correctly.
*   **Attacker Peer (Sybil Node):** A malicious node controlled by an adversary. When queried, these nodes exclusively return lists of other known attacker nodes to poison honest peers' routing tables.
*   **SCION Validator Peer:** An honest peer cryptographically registered with a verifiable identity via SCION’s Control-Plane Public Key Infrastructure (CP-PKI).

### 1.2 DHT and Lookup Mechanics
*   **Routing Tables:** Modeled after Kademlia's k-buckets, each node maintains a routing table with a maximum capacity of `k = 20` (`K_ROUTING_TABLE`).
*   **Lookups:** In each simulation step, honest nodes perform a lookup by querying a random peer from their routing table. Lookups return up to 5 peers (`LOOKUP_PEERS_RETURNED`).
*   **Protection Logic:** PILA-based authentication is modeled via a deterministic rule. An honest peer is considered **protected** if it has at least one SCION Validator in its routing table. Protected peers cross-reference lookup responses and discard malicious/untrusted peers. Unprotected peers blindly accept all lookup responses.

### 1.3 Routing Table Update Strategies
The simulation tests two distinct eviction/update strategies for when a routing table bucket is full:
1.  **Default Strategy:** Emulates standard Kademlia behavior. A newly discovered peer replaces a completely random entry in the full bucket.
2.  **Prefer-SCION Strategy:** An active retention mechanism. A newly discovered SCION validator is preferentially kept, actively evicting a non-validator peer to make room.

### 1.4 Benchmarking and Execution Automation
The framework is built for highly scalable, automated testing:
*   **Parameter Grids:** The benchmarking script evaluates various network sizes (`2000, 5000, 10000` nodes), attacker fractions (`20%, 40%, 60%`), and SCION validator deployments (`0% to 20%`).
*   **Parallel Execution:** `benchmark.py` uses Python's multiprocessing pool to run hundreds of simulation combinations concurrently across multiple CPU cores, aggregating the statistical outputs into a consolidated master CSV.

## 2. Quick Start Guide: Running the Simulation & Plotting

Follow these steps to set up the environment, run the full benchmarking suite, and generate the evaluation plots. 

### Step 1: Set up a Virtual Environment
It is highly recommended to run the simulation inside an isolated Python virtual environment to prevent dependency conflicts. Open your terminal and run:

```bash
# Create a new virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (Command Prompt):
# venv\Scripts\activate
```

### Step 2: Install Dependencies
With the virtual environment activated, install the required Python packages (such as `networkx`, `pandas`, `numpy`, and `tqdm`):

```bash
pip install -r requirements.txt
```

### Step 3: Run the Benchmark Simulation
Execute the parallel benchmarking script. This will systematically test the network across different node sizes, attacker fractions, and SCION deployment scales.

```bash
python3 benchmark.py
```
> ⚠️ **Note:** Depending on your machine's CPU core count, this benchmarking process relies on heavy parallel execution and **will take a few hours to complete**. You can track the progress via the terminal output bars.

### Step 4: Aggregate the Results
Once the benchmark finishes, it will leave multiple CSV files in your root directory. Run the aggregation script to parse the filenames, extract the configuration parameters, and compile everything into a single master dataset.

```bash
python3 aggregate_results.py
```
*This script automatically creates a `plots/` directory and saves the compiled data as `plots/master_results.csv`.*

### Step 5: Generate the Plots
Finally, navigate into the `plots` directory and run the plotting script to visualize the mitigation of Sybil attacks based on your aggregated data.

```bash
cd plots
python3 plot_results.py
```
This will process the `master_results.csv` and generate the final graphical figures (e.g., PDFs or PNGs) demonstrating the performance of the `Prefer-SCION` strategy versus standard Kademlia routing.