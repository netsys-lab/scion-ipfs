import random
import networkx as nx
import numpy as np

# --- Configuration ---
K_ROUTING_TABLE = 20  # Corresponds to k in Kademlia DHTs
LOOKUP_PEERS_RETURNED = 5 # Number of peers returned in a simulated lookup

class PeerNode:
    """
    Represents a single peer in the simulated IPFS network.
    """
    def __init__(self, node_id, is_attacker=False, is_scion_validator=False):
        self.id = node_id
        self.is_attacker = is_attacker
        self.is_scion_validator = is_scion_validator
        self.routing_table = []

    def get_attacker_ratio(self):
        """Calculates the fraction of attackers in this node's routing table."""
        if not self.routing_table:
            return 0.0
        attacker_count = sum(1 for peer in self.routing_table if peer.is_attacker)
        return attacker_count / len(self.routing_table)

    def perform_lookup(self, network_nodes):
        """Simulates a peer lookup."""
        if self.is_attacker:
            attackers = [node for node in network_nodes if node.is_attacker and node.id != self.id]
            return random.sample(attackers, min(len(attackers), LOOKUP_PEERS_RETURNED))
        else:
            return random.sample(self.routing_table, min(len(self.routing_table), LOOKUP_PEERS_RETURNED))

    def update_routing_table(self, new_peers, kademlia_strategy='default'):
        """
        Updates the routing table with new peers, using a specified eviction strategy.

        Args:
            new_peers (list): A list of PeerNode objects to potentially add.
            kademlia_strategy (str): 'default' or 'prefer_scion'.
        """
        for peer in new_peers:
            if peer.id == self.id or peer in self.routing_table:
                continue

            if len(self.routing_table) < K_ROUTING_TABLE:
                self.routing_table.append(peer)
            else:
                # Bucket is full, apply eviction strategy
                if kademlia_strategy == 'prefer_scion':
                    # Find a non-SCION peer to evict.
                    non_scion_peers = [p for p in self.routing_table if not p.is_scion_validator]
                    if peer.is_scion_validator and non_scion_peers:
                        # New peer is SCION, and there's a non-SCION peer to evict.
                        evict_candidate = random.choice(non_scion_peers)
                        self.routing_table[self.routing_table.index(evict_candidate)] = peer
                    elif not peer.is_scion_validator and non_scion_peers:
                        # New peer is non-SCION, evict another non-SCION.
                        evict_candidate = random.choice(non_scion_peers)
                        self.routing_table[self.routing_table.index(evict_candidate)] = peer
                    elif peer.is_scion_validator and not non_scion_peers:
                        # New peer is SCION, but bucket is full of SCION peers. Evict randomly.
                        self.routing_table[random.randint(0, K_ROUTING_TABLE - 1)] = peer
                    # else: new peer is non-SCION and bucket is full of SCION peers. Reject.
                else:  # Default strategy
                    # Evict a random entry.
                    self.routing_table[random.randint(0, K_ROUTING_TABLE - 1)] = peer


class SybilSimulation:
    """
    Manages the entire simulation, network, and experiment steps.
    """
    def __init__(self, num_nodes, attacker_fraction, scion_fraction, 
                 scion_deployment_strategy='random', kademlia_strategy='default'):
        self.num_nodes = num_nodes
        self.attacker_fraction = attacker_fraction
        self.scion_fraction = scion_fraction
        self.scion_deployment_strategy = scion_deployment_strategy
        self.kademlia_strategy = kademlia_strategy  # NEW
        
        self.graph = None
        self.nodes = []
        self.attackers = []
        self.scion_validators = []
        self.honest_vulnerable_nodes = []
        
        self._setup_network()

    def _setup_network(self):
        """Creates the network topology and assigns roles to nodes."""
        # ... (This method remains unchanged from the previous version) ...
        self.graph = nx.barabasi_albert_graph(self.num_nodes, 3, seed=42)
        node_ids = list(self.graph.nodes())
        random.shuffle(node_ids)

        num_attackers = int(self.num_nodes * self.attacker_fraction)
        num_scion = int(self.num_nodes * self.scion_fraction)

        self.nodes = [PeerNode(i) for i in range(self.num_nodes)]
        attacker_ids = node_ids[:num_attackers]
        
        if self.scion_deployment_strategy == 'random':
            potential_scion_ids = node_ids[num_attackers:]
            scion_ids = random.sample(potential_scion_ids, min(num_scion, len(potential_scion_ids)))
        elif self.scion_deployment_strategy == 'hub':
            potential_scion_ids = [nid for nid in node_ids if nid not in attacker_ids]
            degrees = sorted(self.graph.degree(potential_scion_ids), key=lambda item: item[1], reverse=True)
            scion_ids = [node_id for node_id, deg in degrees[:num_scion]]
        else:
            raise ValueError(f"Unknown SCION deployment strategy: {self.scion_deployment_strategy}")

        for node in self.nodes:
            if node.id in attacker_ids:
                node.is_attacker = True
                self.attackers.append(node)
            elif node.id in scion_ids:
                node.is_scion_validator = True
                self.scion_validators.append(node)
            else:
                self.honest_vulnerable_nodes.append(node)

        for node in self.nodes:
            neighbors = [self.nodes[n_id] for n_id in self.graph.neighbors(node.id)]
            node.routing_table = random.sample(neighbors, min(len(neighbors), K_ROUTING_TABLE))


    def _run_simulation_step(self):
        """Runs one step of the simulation."""
        nodes_to_update = self.honest_vulnerable_nodes + self.scion_validators
        random.shuffle(nodes_to_update)

        for node in nodes_to_update:
            if not node.routing_table:
                continue
            
            queried_peer = random.choice(node.routing_table)
            newly_discovered_peers = queried_peer.perform_lookup(self.nodes)

            has_scion_contact = any(p.is_scion_validator for p in node.routing_table)

            if has_scion_contact:
                if not queried_peer.is_attacker:
                    # Pass the kademlia strategy to the update function
                    node.update_routing_table(newly_discovered_peers, self.kademlia_strategy)
            else:
                node.update_routing_table(newly_discovered_peers, self.kademlia_strategy)

    def run(self, num_steps):
        """Runs the full simulation for a number of steps."""
        for i in range(num_steps):
            self._run_simulation_step()

    def analyze_results(self):
        """Calculates the final attacker ratio for the vulnerable nodes."""
        if not self.honest_vulnerable_nodes:
            return 0.0
        
        ratios = [node.get_attacker_ratio() for node in self.honest_vulnerable_nodes]
        return np.mean(ratios)