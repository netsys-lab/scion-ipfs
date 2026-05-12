# SCION-IPFS Developer Documentation

This document is the comprehensive reference for developers who want to understand, deploy, integrate, or contribute to the SCION-IPFS library — an extension of IPFS (via Kubo and libp2p) that runs natively over the SCION next-generation Internet architecture.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Map](#2-repository-map)
3. [Prerequisites and Setup](#3-prerequisites-and-setup)
4. [SCION Multiaddress Format](#4-scion-multiaddress-format)
5. [SCION QUIC Transport](#5-scion-quic-transport)
6. [PILA Cryptographic Peer Verification](#6-pila-cryptographic-peer-verification)
7. [Path Selection Strategies](#7-path-selection-strategies)
8. [Configuration Reference](#8-configuration-reference)
9. [Security Simulation Framework](#9-security-simulation-framework)
10. [Security Properties](#10-security-properties)
11. [Contributing and Upstream Status](#11-contributing-and-upstream-status)

---

## 1. Project Overview

SCION-IPFS integrates IPFS with the SCION (Scalability, Control, and Isolation on Next-Generation Networks) Internet architecture to address fundamental limitations of IPFS when running over conventional BGP-based Internet routing.

### Motivation

Standard IPFS relies on the BGP-routed Internet for peer communication. This introduces three structural problems:

- **Routing attacks:** BGP lacks intrinsic security; prefixes can be hijacked, redirecting or blackholing traffic.
- **Sybil/Eclipse attacks:** Creating IPFS peer identities is free, enabling adversaries to flood DHT routing tables with malicious entries.
- **Performance ceiling:** BGP forces single-path routing, leaving available network capacity unused and suffering from high-latency "long tails" on inter-continental transfers.

### What SCION-IPFS Provides

By running IPFS natively over SCION, the library delivers:

| Property | Mechanism |
|---|---|
| Authenticated peer identity | PILA certificates bound to SCION AS registration |
| BGP hijacking immunity | SCION Path Construction Beacons (PCBs) + endhost path control |
| Multi-path throughput | Parallel QUIC connections, one per SCION path |
| Intelligent path selection | 8 pluggable strategies (bandwidth-aware, latency-aware, disjoint, etc.) |
| Backward compatibility | SCION transport coexists with standard TCP/WebSocket/IP-QUIC |

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Kubo (IPFS node)                   │
│                                                     │
│  ┌───────────┐   ┌──────────────────────────────┐  │
│  │  Bitswap  │   │  Path Selection Strategy     │  │
│  │  Server   │──▶│  (PathSelector interface)    │  │
│  └───────────┘   └──────────────────────────────┘  │
│        │                      │                     │
│  ┌─────▼──────────────────────▼──────────────────┐  │
│  │            libp2p (SCION transport)           │  │
│  │  Connection Pool: [QUIC/path₁, QUIC/path₂…]  │  │
│  └───────────────────────────────────────────────┘  │
│        │                                            │
│  ┌─────▼───────────────────────────────────────┐   │
│  │    PILA TLS 1.3 Handshake Extension        │   │
│  │  (CA cert → AS cert → Endhost cert)        │   │
│  └────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────┘
                         │
                  SCION Daemon
                  (path discovery)
                         │
              ┌──────────▼──────────┐
              │   SCION Network     │
              │   (paths, PCBs)     │
              └─────────────────────┘
```

---

## 2. Repository Map

The implementation is spread across several repositories. All are required for a full deployment.

### Core Implementation Repos

| Repository | Branch | Purpose |
|---|---|---|
| [`netsys-lab/scion-ipfs`](https://github.com/netsys-lab/scion-ipfs) | `main` | Project documentation (this repo) |
| [`netsys-lab/go-libp2p`](https://github.com/netsys-lab/go-libp2p/tree/feature/scion-quic-transport) | `feature/scion-quic-transport` | SCION QUIC transport + PILA TLS extension |
| [`netsys-lab/boxo`](https://github.com/netsys-lab/boxo/tree/feature/scion-boxo) | `feature/scion-boxo` | Path selection strategies in the Bitswap server |

### Upstream Integration (Pending)

| PR / Issue | Repository | Status |
|---|---|---|
| [PR #285](https://github.com/multiformats/go-multiaddr/pull/285) | `multiformats/go-multiaddr` | SCION multiaddr protocol — awaiting merge |
| [PR #325](https://github.com/multiformats/multicodec/pull/325) | `multiformats/multicodec` | SCION multicodec table entry — awaiting merge |
| [Issue #3458](https://github.com/libp2p/go-libp2p/issues/3458) | `libp2p/go-libp2p` | Upstream discussion for SCION transport integration |

> The `go-libp2p` transport PR is intentionally withheld until `go-multiaddr` PR #285 merges, since `go-multiaddr` is a dependency of `go-libp2p` and its validation logic must be in place first.

### Key Commit Reference

- [PILA integration into go-libp2p TLS](https://github.com/netsys-lab/go-libp2p/commit/b4c5ab18ee86c222640bf4c1566e6e7fa9ee9e2b) — the specific commit implementing server-side certificate fetching and client-side TLS verification wrapper.

---

## 3. Prerequisites and Setup

### 3.1 System Requirements

- **Go 1.21+** — required to build `go-libp2p` and `boxo` branches
- **SCION daemon** — the local SCION endhost daemon must be running and reachable; it provides path discovery to the transport layer
- **Membership in a SCION network** — either [SCIONLab](https://www.scionlab.org/) (global research testbed) or a production network such as SCIERA

### 3.2 Cloning the Implementation Branches

```bash
# Clone the SCION-extended libp2p
git clone -b feature/scion-quic-transport https://github.com/netsys-lab/go-libp2p.git

# Clone the SCION-extended boxo (Bitswap + path selection)
git clone -b feature/scion-boxo https://github.com/netsys-lab/boxo.git
```

Use `replace` directives in your `go.mod` to point Kubo at these local forks:

```go
replace (
    github.com/libp2p/go-libp2p => ../go-libp2p
    github.com/ipfs/boxo        => ../boxo
)
```

### 3.3 PILA Service (Optional but Recommended)

PILA-based peer verification requires access to a PILA certificate service co-located with the SCION AS. Configure it via environment variables before starting the IPFS node:

```bash
# URL of the PILA certificate service in your SCION AS
export SCION_PILA_URL="http://localhost:8080"

# Path to the folder containing SCION TRC (Trust Root Configuration) certificates
# used by the client side to verify remote peers
export SCION_PILA_CERTS_FOLDER="/etc/scion/certs"
```

If `SCION_PILA_URL` is not set, the node starts without PILA and falls back to standard libp2p peer-ID-only authentication.

### 3.4 Starting an IPFS Node over SCION

Once the above is in place, start the node as you would a standard Kubo node. The SCION transport is registered automatically and will be preferred for peers that advertise a `/scion/` multiaddress.

---

## 4. SCION Multiaddress Format

To enable `libp2p` to dial and listen on SCION endpoints, a new `multiaddr` protocol was defined following the self-describing multiaddress convention.

### Format Specification

```
/scion/<ISD-AS>/<Host-Multiaddr>
```

| Component | Description |
|---|---|
| `scion` | Protocol name |
| `<ISD-AS>` | Isolation Domain and Autonomous System identifier (e.g., `19-ffaa:1:f`) |
| `<Host-Multiaddr>` | Encapsulated standard IP/UDP address of the endhost |

### Example

A node in ISD 19, AS `ffaa:1:f`, at IP `10.0.0.1` on UDP port `123`:

```
/scion/19-ffaa:1:f/ip4/10.0.0.1/udp/123
```

### Status

The protocol definition has been submitted to:
- [`multiformats/multicodec` PR #325](https://github.com/multiformats/multicodec/pull/325) — table registration
- [`multiformats/go-multiaddr` PR #285](https://github.com/multiformats/go-multiaddr/pull/285) — Go implementation

The format is already usable via the `netsys-lab/go-libp2p` fork while upstream PRs are pending.

---

## 5. SCION QUIC Transport

The SCION transport is implemented as a modular component within `libp2p` in the [`netsys-lab/go-libp2p`](https://github.com/netsys-lab/go-libp2p/tree/feature/scion-quic-transport) `feature/scion-quic-transport` branch.

### 5.1 Path Pinning and Connection Pooling

Standard QUIC congestion control assumes a stable, single network path. Switching paths mid-stream disrupts RTT estimates and packet ordering. To support SCION's inherent multipath capability without breaking QUIC:

1. **Discovery:** On first contact with a peer, the transport queries the local SCION daemon for all available end-to-end paths to that peer's SCION address.
2. **Connection pinning:** A separate QUIC connection is established for each selected path. This "pins" the connection to a stable path, preserving QUIC's congestion invariants.
3. **Connection pool:** All pinned connections are stored in a pool for the duration of the session and reused for subsequent transfers to the same peer.

### 5.2 Integration with Bitswap

The connection pool is exposed to the upper layer — specifically to IPFS's Bitswap data exchange protocol. The workflow for a block send:

1. The Bitswap server has a content block ready to send (an *envelope*).
2. It calls `QueryPaths()` on the network layer to retrieve the available SCION paths to the target peer.
3. The active `PathSelector` strategy (see [Section 7](#7-path-selection-strategies)) picks the optimal path.
4. The context is annotated with the chosen path via `network.ViaPath(ctx, chosenPath)`.
5. The block is sent over the pinned QUIC connection for that path via `network.SendMessage()`.

This allows IPFS to saturate multiple SCION paths simultaneously for a single logical peer, increasing both resilience and throughput.

### 5.3 Backward Compatibility

The SCION transport is registered **alongside** the standard transports (TCP, WebSocket, QUIC-over-IP):

- **SCION-enabled peers** advertise `/scion/` addresses and prefer the SCION transport when connecting to other SCION-enabled peers.
- **Standard IP-only peers** continue to use TCP/WebSocket/IP-QUIC and are unaffected.
- A SCION node can thus participate in a mixed swarm of SCION and IP peers simultaneously, as demonstrated in the SCIERA production experiment.

---

## 6. PILA Cryptographic Peer Verification

PILA (Pervasive Internet-Wide Low-Latency Authentication) binds an IPFS peer's network identity to its cryptographically registered SCION AS. The implementation extends `libp2p`'s existing TLS 1.3 handshake without replacing the standard libp2p peer-ID verification mechanism.

Source: [`go-libp2p` PILA commit](https://github.com/netsys-lab/go-libp2p/commit/b4c5ab18ee86c222640bf4c1566e6e7fa9ee9e2b)

### 6.1 Certificate Chain

When PILA is active, each peer presents a three-level certificate chain during the TLS handshake:

```
CA Certificate
    └── AS Certificate (identifies the SCION Autonomous System)
            └── Endhost Certificate (identifies the specific IPFS node)
```

The receiving peer verifies this chain against the SCION Trust Root Configuration (TRC) for the relevant Isolation Domain (ISD) and confirms that the peer's physical IP address matches the address bound in the certificate.

### 6.2 Server-Side: Fetching and Presenting the Certificate

When the SCION transport starts listening (`transport.Listen()`), it checks for `SCION_PILA_URL`. If set, it:

1. Reads the node's existing libp2p private key from the base `tls.Config`.
2. Generates a Certificate Signing Request (CSR) using that key.
3. Fetches a PILA certificate chain from the local SCION AS via the PILA service.
4. Converts the chain to a `tls.Certificate` and appends it to `tlsConf.GetConfigForClient`.

```go
func (t *transport) Listen(addr ma.Multiaddr) (tpt.Listener, error) {
    var scionCerts []tls.Certificate
    pilaURL := os.Getenv("SCION_PILA_URL")
    if pilaURL != "" {
        conf := t.identity.GetConfig()
        if len(conf.Certificates) > 0 {
            key := conf.Certificates[0].PrivateKey.(*ecdsa.PrivateKey)
            client := scionpila.NewSCIONPilaClient(pilaURL)

            csr, err := scionpila.NewCertificateSigningRequest(key)
            if err != nil {
                return nil, err
            }

            certificate, err := client.FetchCertificateFromSigningRequest(udpAddr.String(), csr)
            if err != nil {
                return nil, err
            }

            scionCerts, err = scionpila.CreateTLSCertificate(certificate, key)
            if err != nil {
                return nil, err
            }
        }
    }

    tlsConf.GetConfigForClient = func(_ *tls.ClientHelloInfo) (*tls.Config, error) {
        conf, _ := t.identity.ConfigForPeer("")
        if len(scionCerts) > 0 {
            conf.Certificates = append(conf.Certificates, scionCerts...)
        }
        return conf, nil
    }
}
```

### 6.3 Client-Side: Verifying the Remote Peer

When dialing a SCION peer, the client wraps the existing `VerifyPeerCertificate` function. If `SCION_PILA_CERTS_FOLDER` is set, it first runs SCION TRC verification, then falls through to the original libp2p peer-ID check:

```go
pilaCertsFolder := os.Getenv("SCION_PILA_CERTS_FOLDER")
if pilaCertsFolder != "" {
    remoteVerifyFunc := scionpila.VerifyQUICCertificateChainsHandler(
        pilaCertsFolder, udpAddr.String(),
    )
    f := tlsConf.VerifyPeerCertificate
    tlsConf.VerifyPeerCertificate = func(rawCerts [][]byte, verifiedChains [][]*x509.Certificate) error {
        if err := remoteVerifyFunc(rawCerts, verifiedChains); err != nil {
            return err
        }
        if f != nil {
            return f(rawCerts, verifiedChains)
        }
        return nil
    }
}
```

### 6.4 Security Impact

Because obtaining a valid PILA certificate requires actual control over a registered SCION AS, creating thousands of fake peer identities becomes economically and cryptographically prohibitive — the attacker would need to compromise the SCION CP-PKI. This eliminates the practical viability of large-scale Sybil and Eclipse attacks.

---

## 7. Path Selection Strategies

Path selection is implemented in [`netsys-lab/boxo`](https://github.com/netsys-lab/boxo/tree/feature/scion-boxo) (`feature/scion-boxo` branch) inside the Bitswap server. The implementation uses the **Strategy Pattern** to decouple the selection logic from the `sendBlocks` hot-path.

### 7.1 The Interface

```go
type PathSelector interface {
    SelectPath(
        paths []snet.Path,
        usage map[snet.PathFingerprint]int,
        rates map[string]float64,
    ) snet.Path
}
```

| Parameter | Description |
|---|---|
| `paths` | All available SCION paths to the peer (from daemon) |
| `usage` | Map of path fingerprint → current in-flight envelope count |
| `rates` | Map of path fingerprint → historically estimated bandwidth (bytes/s) |

### 7.2 The Eight Strategies

| Code | Name | Description |
|---|---|---|
| 1 | **Random** | Assigns a path completely at random, regardless of load or metrics |
| 2 | **Single Shortest (Baseline)** | Always uses the single shortest-hop path; mirrors conventional BGP routing |
| 3 | **First Free Random** | Selects randomly among paths not currently in use |
| 4 | **First Free Lowest Latency** | Among free paths, picks the one with the lowest static metadata latency |
| 5 | **First Free Lowest Latency (sub)** | Like strategy 4, with a secondary sub-value latency fallback for tie-breaking |
| 6 | **First Free Most Disjoint** | Prefers paths that share the fewest network interfaces with paths in use |
| 7 | **First Free Shortest** | Among free paths, picks the one with the fewest hops |
| 8 | **First Free Highest Bandwidth** | Picks the free path with the highest historically measured bandwidth — **best overall performance** |

### 7.3 Factory Method

Strategies are selected at initialization time via an integer configuration value:

```go
func getPathSelector(strat int) PathSelector {
    switch strat {
    case 1: return CompletelyRandomSelector{}
    case 2: return &SingleShortestPathSelector{}
    case 3: return FirstFreeRandomSelector{}
    case 4: return FirstFreeLowestLatencySelector{}
    case 5: return FirstFreeLowestLatencySubSelector{}
    case 6: return FirstFreeMostDisjointSelector{}
    case 7: return FirstFreeShortestSelector{}
    case 8: return FirstFreeHighestBandwidthSelector{}
    default: return CompletelyRandomSelector{}
    }
}
```

### 7.4 Bandwidth-Aware Strategy (Recommended)

Strategy 8 — `FirstFreeHighestBandwidthSelector` — is the strategy validated to achieve the best real-world performance (2.9× speedup over single-path baseline in SCIONLab tests):

```go
type FirstFreeHighestBandwidthSelector struct{}

func (s FirstFreeHighestBandwidthSelector) SelectPath(
    paths []snet.Path,
    usage map[snet.PathFingerprint]int,
    rates map[string]float64,
) snet.Path {
    pathsWithBw := filter(paths, func(p snet.Path) bool {
        _, ok := rates[snet.Fingerprint(p).String()]
        return ok
    })

    if len(pathsWithBw) > 0 {
        sort.Slice(pathsWithBw, func(i, j int) bool {
            return rates[snet.Fingerprint(pathsWithBw[i]).String()] >
                rates[snet.Fingerprint(pathsWithBw[j]).String()]
        })
        for _, path := range pathsWithBw {
            if u, ok := usage[snet.Fingerprint(path)]; !ok || u == 0 {
                return path
            }
        }
    }
    // Fallback when no bandwidth telemetry is available yet
    return firstFree(sortShortest(paths), usage)
}
```

### 7.5 Integration in `sendBlocks`

The strategy pattern keeps the Bitswap hot-path clean:

```go
func (bs *Server) sendBlocks(ctx context.Context, env *decision.Envelope) {
    paths, err := bs.network.QueryPaths(ctx, env.Peer)
    var fprint snet.PathFingerprint

    if err == nil && len(paths) > 0 {
        chosenPath := bs.pathSelector.SelectPath(paths, bs.pathUsage, bs.counters.AverageRatePerPath)
        fprint = snet.Fingerprint(chosenPath)
        ctx = network.ViaPath(ctx, chosenPath)
    }

    bs.pathUsage[fprint] += 1
    err = bs.network.SendMessage(ctx, env.Peer, env.Message)
    // ... cleanup ...
}
```

---

## 8. Configuration Reference

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SCION_PILA_URL` | No | HTTP URL of the local PILA certificate service (e.g., `http://localhost:8080`). If unset, PILA verification is disabled. |
| `SCION_PILA_CERTS_FOLDER` | No | Filesystem path to a directory containing SCION TRC certificate files used for client-side peer verification. Must be set for incoming PILA validation to function. |

### Path Selection Strategy Integer Codes

Set the strategy by passing the integer code to the Bitswap server's path selector factory (see [Section 7.3](#73-factory-method)):

| Value | Strategy |
|---|---|
| `1` | Random |
| `2` | Single Shortest (BGP-like baseline) |
| `3` | First Free Random |
| `4` | First Free Lowest Latency |
| `5` | First Free Lowest Latency (sub-value fallback) |
| `6` | First Free Most Disjoint |
| `7` | First Free Shortest |
| `8` | **First Free Highest Bandwidth** (recommended) |

---

## 9. Security Simulation Framework

The `task3/` directory contains a complete Python simulation suite for evaluating the effectiveness of SCION-based peer validation against Sybil attacks in IPFS-like Kademlia DHTs.

Source: [`task3/simulation-framework.md`](../task3/simulation-framework.md)

### 9.1 Framework Components

| File | Role |
|---|---|
| `task3/simulation.py` | Core discrete-time event simulator: `PeerNode`, `SybilSimulation` classes |
| `task3/run_experiments.py` | Single-run experiment runner with configurable parameters via argparse |
| `task3/benchmark.py` | Parallelized benchmark suite over a full parameter grid (uses multiprocessing) |
| `task3/aggregate_results.py` | Parses result CSV filenames and consolidates into `plots/master_results.csv` |

### 9.2 Simulation Parameters

| Parameter | Values used in evaluation |
|---|---|
| Network size (`N`) | 2,000 / 5,000 / 10,000 nodes |
| Attacker fraction | 20% / 40% / 60% of nodes |
| SCION validator fraction | 0%, 1%, 2%, 3%, 5%, 7%, 10%, 15%, 20% |
| Kademlia k-bucket size | 20 |
| Peers returned per lookup | 5 |
| Simulation steps | 75 (convergence point) |
| Runs per scenario | 10 (for statistical confidence) |

### 9.3 Quick Start

```bash
cd task3

# Step 1: Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# Step 2: Install dependencies
pip install -r requirements.txt   # tqdm, pandas, networkx, matplotlib, seaborn

# Step 3: Run the full benchmark (parallel, takes several hours)
python3 benchmark.py

# Step 4: Aggregate all result CSVs into a master dataset
python3 aggregate_results.py      # outputs plots/master_results.csv

# Step 5: Generate plots
cd plots
python3 plot_results.py
```

> **Note:** `benchmark.py` uses Python's `multiprocessing` pool on N−2 CPU cores. On a modern workstation the full grid (all node sizes, attacker fractions, validator fractions, strategies) takes several hours.

### 9.4 Running a Single Experiment

For quick exploration without the full benchmark:

```bash
python3 run_experiments.py \
    --num_nodes 2000 \
    --attacker_fraction 0.40 \
    --scion_fraction 0.10 \
    --strategy prefer_scion
```

---

## 10. Security Properties

### 10.1 BGP Hijacking Immunity

SCION disseminates routing information via Path Construction Beacons (PCBs), which are cryptographically signed at each hop by core ASes. No intermediate network can forge or redirect these beacons. Because the SCION multiaddr (`/scion/<ISD-AS>/...`) embeds the full verified path in each packet header (Packet-Carried Forwarding State, PCFS), intermediate routers are strictly bound to the mandated path. Traffic cannot be hijacked mid-transit by a malicious network.

### 10.2 Man-in-the-Middle Mitigation

A MitM attack over SCION would require simultaneously compromising the explicit network path **and** forging the endpoint's PILA certificate. The PILA integration verifies on the client side that the remote peer's physical IP address exactly matches the address cryptographically bound in its TRC-validated certificate chain. Both conditions are required; the combination is architecturally and mathematically infeasible under normal adversary models.

### 10.3 Sybil and Eclipse Attack Resistance

Standard IPFS makes peer-ID creation free. With PILA, generating a valid libp2p connection credential requires possessing a legitimate SCION AS registration and a corresponding PILA certificate. An attacker building thousands of authenticated identities would need to compromise the SCION CP-PKI — an infeasible requirement. Quantitatively, the simulation shows:

- **Default (passive) Kademlia:** Even with 20% SCION validators, routing tables remain >90% polluted under 60% attacker load.
- **Prefer-SCION (active retention):** Same conditions → only 29% pollution — a 71% reduction.
- **Critical threshold:** Protection becomes significant once >10% of network nodes are SCION validators.

### 10.4 DDoS and Link Failure Resilience

SCION's native multipath support means the path selection strategies (Section 7) can instantly reroute envelopes away from congested or downed links. Unlike BGP (minutes to converge), SCION border routers detect link failures in milliseconds, and the `FirstFreeHighestBandwidthSelector` filters in real-time based on observed bandwidth telemetry, ensuring the application layer is unaffected by targeted link disruptions.

---

## 11. Contributing and Upstream Status

### Current State

All core implementation work is complete on the project's forks. The upstream integration path is:

1. **`multiformats/go-multiaddr` PR #285** merges → SCION multiaddr protocol is part of the standard library.
2. Once that merges, the **`go-libp2p` transport PR** can be opened (held back because `go-multiaddr` is a dependency).
3. Ongoing upstream discussion at **`libp2p/go-libp2p` issue #3458** tracks SCION's integration with core maintainers.

### Contributing to the Forks

```bash
# Transport and PILA work
git clone -b feature/scion-quic-transport https://github.com/netsys-lab/go-libp2p.git
cd go-libp2p
# ... make changes, run tests ...
go test ./p2p/transport/scion/...

# Path selection work
git clone -b feature/scion-boxo https://github.com/netsys-lab/boxo.git
cd boxo
go test ./bitswap/...
```

### Related Documentation

| Document | Location |
|---|---|
| Native SCION libp2p integration (Task 1) | [`task1/implementation.md`](../task1/implementation.md) |
| Path selection strategies detail (Task 2) | [`task2/path-selection.md`](../task2/path-selection.md) |
| PILA integration detail (Task 2) | [`task2/scion-pila.md`](../task2/scion-pila.md) |
| Qualitative security analysis (Task 3) | [`task3/security-analysis.md`](../task3/security-analysis.md) |
| Sybil simulation report (Task 3) | [`task3/report.md`](../task3/report.md) |
| Simulation framework guide (Task 3) | [`task3/simulation-framework.md`](../task3/simulation-framework.md) |
| Performance benchmarks (Task 4) | [`task4/performance-report.md`](performance-report.md) |
| Final performance report (Task 4) | [`task4/final-performance-report.md`](final-performance-report.md) |
