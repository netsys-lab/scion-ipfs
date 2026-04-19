# Qualitative Analysis: Resilience of IPFS over SCION against Routing and Identity Attacks

## Overview

The standard InterPlanetary File System (IPFS) operates as an overlay network atop the conventional, BGP-routed Internet. As a result, it inherits fundamental vulnerabilities from the underlay: susceptibility to routing attacks (BGP hijacking), Man-in-the-Middle (MitM) interceptions, and identity-spoofing (Sybil/Eclipse attacks). 

By integrating IPFS natively with the SCION next-generation Internet architecture and extending `libp2p` to support Pervasive Internet-Wide Low-Latency Authentication (PILA), these attack vectors are fundamentally neutralized. This report provides a qualitative analysis of how the implementation's architecture provides deep resilience against these three critical threat models.

---

## 1. Resilience Against BGP Hijacking and Routing Attacks

### The Threat: BGP Vulnerabilities
In the traditional Internet, the Border Gateway Protocol (BGP) lacks intrinsic security. Adversaries can execute prefix hijacking or route leaks to illegitimately announce ownership of IP ranges. This allows an attacker to redirect, intercept, or blackhole traffic on a massive scale.

### The SCION Defense: Secure Beaconing and Path Control
SCION fundamentally eliminates this entire class of routing attacks through its secure control plane and packet-carried forwarding state (PCFS):
*   **Path Construction Beacons (PCBs):** Route information is disseminated via PCBs, which are cryptographically signed at each hop by the core Autonomous Systems (ASes). Routing announcements cannot be forged.
*   **Endhost Path Control:** SCION grants the endhost complete control over the network path. 
*   **Implementation Impact:** By implementing the native `/scion/<ISD-AS>/<Host-Multiaddr>` multiaddress format within `go-multiaddr`, our `libp2p` implementation empowers the IPFS node to explicitly define and select its routing path. Because the full, verified path is embedded in the packet header, intermediate routers strictly follow the mandated path, making it impossible for malicious networks to hijack or redirect the traffic mid-transit.

---

## 2. Mitigation of Man-in-the-Middle (MitM) Attacks

### The Threat: Intercepting P2P Traffic
Even though IPFS protects data integrity using cryptographic hashes (CIDs), the exchange of provider records and peer discovery requests remains vulnerable. If an attacker hijacks a route, they can execute a MitM attack, intercepting peer discovery queries and injecting malicious responses.

### The SCION + PILA Defense: Verifiable Paths and Identities
To execute a MitM attack over SCION, an adversary would not only need to compromise the explicit network path but also spoof the endpoint identity. Our implementation prevents this through the combination of SCION's path verification and the PILA integration.

*   **PILA Integration:** We extended `libp2p`'s TLS 1.3 handshake to include PILA certificate chains. When a node dials a SCION multiaddress, the receiving server dynamically presents a certificate chain consisting of: `CA Certificate -> AS Certificate -> Endhost Certificate`.
*   **Implementation Impact:** On the client-side, we intercept the TLS verification via a clean wrapper around `VerifyPeerCertificate`. The client verifies the peer's certificate against the SCION Trust Root Configuration (TRC) to ensure the peer's physical IP address exactly matches the cryptographically bound SCION address. Because the traffic travels over a tamper-proof path and the endpoint is cryptographically verified against the TRC, MitM interceptions are mathematically and architecturally neutralized.

---

## 3. Defense Against Sybil and Eclipse Attacks

### The Threat: Costless Pseudonymous Identities
In a Sybil attack, an adversary spins up thousands of cheap, pseudonymous identities to overwhelm honest nodes, poisoning their Kademlia DHT routing tables. This leads to an Eclipse attack, isolating the honest node from the legitimate network.

### The SCION + PILA Defense: Economic and Cryptographic Scarcity
Standard IPFS makes creating new peer IDs free. Our SCION implementation shifts the root of trust to the physical network topology, introducing severe economic and cryptographic friction for attackers.

*   **Tying Identity to Topology:** With the PILA implementation, an IPFS node can only generate a valid `libp2p` connection if it possesses a valid SCION PILA certificate.
*   **Implementation Impact:** To generate a valid certificate request (CSR) in our system, the attacker must actually control a legitimate, registered SCION AS. Because each SCION AS must be cryptographically registered within its Isolation Domain (ISD), an attacker cannot simply spoof IP addresses or spin up fake ASes. Creating thousands of authenticated identities would require compromising the core SCION CP-PKI, making large-scale Sybil attacks economically and practically unviable.

---

## 4. Enhanced Resilience via Multipath Path Selection

### The Threat: Link Failures and Targeted DDoS
Beyond cryptographic attacks, attackers often use DDoS attacks to saturate specific network links, causing denial of service. BGP takes minutes to converge and route around such failures.

### The SCION Defense: Concurrent Path Availability
SCION supports native multipath communication. If a link goes down or is congested by an attacker, SCION border routers detect it in milliseconds.

*   **Implementation Impact:** We engineered a secure multipath transport over QUIC and integrated a robust **Strategy Pattern** into the IPFS Bitswap server (`go-bitswap`). 
    *   The transport queries the SCION daemon for all available end-to-end paths and pins a distinct QUIC connection to each one.
    *   Using strategies like `FirstFreeHighestBandwidthSelector`, the implementation dynamically filters available paths based on bandwidth telemetry and current usage.
    *   If an attacker congests one path, the Strategy pattern seamlessly and instantly routes the IPFS data envelopes (blocks) over alternative, healthy SCION connections. 

This multipath agility ensures that even if an adversary successfully degrades a specific network link, the IPFS application layer remains highly resilient, maintaining uninterrupted data retrieval.