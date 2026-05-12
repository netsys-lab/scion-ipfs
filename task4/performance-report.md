# Comparative Performance Analysis of IPFS Content Retrieval: SCION vs. IP

This document provides a detailed comparative analysis of IPFS content retrieval times. The evaluation spans three distinct environments: an emulated baseline, a global research testbed (SCIONLab), and a real-world production network (SCIERA). 

The primary goal of this evaluation is to directly compare the network underlay (SCION’s path-aware, multipath routing vs. conventional IP/BGP single-path routing) and its impact on the real-world decentralized application IPFS (using its reference implementation, Kubo).

---

## 1. Baseline Computational Overhead: Emulated Environment (SEED Emulator)

Before analyzing multipath speedups, the researchers established the baseline computational overhead introduced by SCION's path-aware networking headers and processing.

*   **Setup:** Two Autonomous Systems (ASes) were deployed within the SEED Internet Emulator, connected via a single link. Each AS ran an IPFS node. 
*   **Methodology:** The test consisted of 100 repetitions of fetching a **100 MB file**, comparing native IPFS over BGP/IP against IPFS over SCION.
*   **Results:** 
    *   SCION incurs only a minimal computational penalty. 
    *   The average increase in runtime was approximately **0.1 seconds**.
    *   This translates to a negligible **~2% overhead**.
*   **Conclusion:** The minor overhead caused by SCION's packet-carried forwarding state (PCFS) is highly manageable and serves as a necessary baseline before evaluating the benefits of path diversity.

---

## 2. Path Selection and Multipath Speedup: Testbed Environment (SCIONLab)

SCIONLab is a global, research-focused SCION network that allows for experimentation with inter-domain multipath communication. This phase evaluated how intelligently distributing traffic over multiple SCION paths compares to traditional single-path routing.

*   **Setup:** A **100 MB file** was transferred between two IPFS (Kubo) nodes attached to the OVGU (Otto-von-Guericke University, Germany) Attachment Point and the CMU (Carnegie Mellon University, USA) Attachment Point.
*   **Methodology:** The researchers compared a "Single shortest" path strategy (which acts as a baseline mimicking conventional BGP routing) against several multipath selection strategies.
*   **Results:**
    *   **Baseline (Single shortest):** Retrieving the file took **61.83 seconds**.
    *   **Latency-prioritizing strategies:** Strategies like *First free lowest latency* demonstrated moderate, measurable improvements over the baseline.
    *   **Throughput-optimized strategy:** The *First free highest bandwidth* strategy dynamically selected the fastest available paths based on bandwidth estimations. This strategy drastically reduced the transfer time to **21.63 seconds**.
*   **Conclusion:** By utilizing parallel QUIC connections over diverse SCION paths, IPFS over SCION achieved a massive **2.9x speedup** compared to the single-path BGP-like baseline.

---

## 3. Global Swarm Performance: Real-World Production Network (SCIERA)

To validate the findings in a production-grade setting, the researchers deployed IPFS over SCIERA (SCION Education, Research and Academic Network), a high-performance network connecting over 20 research institutions globally.

*   **Setup:** **11 IPFS nodes** were deployed across **8 geographically diverse ASes** spanning Europe, North America, and Asia. 
*   **Methodology:** The nodes formed a single swarm using both native SCION and conventional Internet (IP) connections. In each run, a different node seeded a random **50 MB file**, which was subsequently fetched by all other peers. SCION transfers utilized the previously validated *highest bandwidth* path selection strategy.
*   **Results (CDF Analysis):**
    *   **Conventional IP:** While some IP-based transfers were fast, the Cumulative Distribution Function (CDF) revealed a severe "long tail" in performance. A significant portion of the IP transfers suffered from high latency, taking **over 30 seconds** to complete.
    *   **IPFS over SCION:** The SCION retrieval time curve rose significantly steeper than the IP curve, indicating that the vast majority of transfers completed much faster. SCION consistently mitigated the high-latency long tail.
*   **Conclusion:** In a real-world, inter-continental swarm scenario, traditional BGP routes often suffer from congestion or suboptimal routing. SCION’s path-aware networking empowers peers to actively bypass these poor links, selecting diverse, high-performance routes. This ensures consistently fast retrieval times and highly reliable performance.

---

## Summary of Findings

1.  **Overhead is Negligible:** The cryptographic and header processing overhead of SCION adds roughly ~2% (0.1s) to baseline transfers, which is easily absorbed by the network benefits.
2.  **Multipath Routing Dominates Single-path:** Intelligent, bandwidth-aware path selection in SCION yields up to a **2.9x reduction** in file retrieval times over inter-continental links compared to single-path defaults.
3.  **Elimination of the "Long Tail":** In real-world, multi-peer swarms, IPFS over SCION provides vastly superior consistency, eliminating the 30+ second high-latency transfers common in conventional BGP-based Internet routing.