# Task 1: Native SCION Support in libp2p

This module implements native SCION networking support within the `libp2p` stack, enabling IPFS nodes to communicate over the SCION next-generation Internet architecture. This implementation addresses the fundamental requirements for **Task 1** of the project roadmap: defining a SCION addressing format and engineering a multipath-capable transport layer.

## Overview

To enable IPFS over SCION, we have modified the core networking layer of Kubo (the IPFS reference implementation) and `libp2p`. This integration allows for:
1.  **SCION Addressing:** A formal definition of SCION endpoints using the `multiaddr` format.
2.  **Multipath Transport:** A modified QUIC transport that leverages SCION's path-awareness to establish parallel connections over different network paths.

## 1. SCION Multiaddresses

To allow `libp2p` to dial and listen on SCION addresses, we introduced a new `multiaddr` protocol. This format adheres to the self-describing nature of multiaddresses, allowing the encapsulation of SCION-specific routing information alongside standard host identifiers.

### Format Specification
A SCION multiaddress is composed of an **ISD-AS** (Isolation Domain - Autonomous System) identifier, followed by the encapsulated host address (e.g., IPv4 or IPv6) and the transport protocol (UDP).

**Structure:**
```text
/scion/<ISD-AS>/<Host-Multiaddr>
```

### Components
*   **Protocol Name:** `scion`
*   **Value:** The ISD-AS string (e.g., `19-ffaa:1:f`).
*   **Encapsulation:** The SCION component wraps the underlying IP/UDP address of the host.

### Example
A node located in ISD 19, AS `ffaa:1:f`, with an internal IP of `10.0.0.1` listening on UDP port `123` is represented as:

```text
/scion/19-ffaa:1:f/ip4/10.0.0.1/udp/123
```

*Status:* This format has been submitted to the [multiformats/multicodec](https://github.com/multiformats/multicodec/pull/325) table and implemented in `go-multiaddr`.

---

## 2. Secure Multipath Transport (QUIC over SCION)

We have implemented a SCION-native transport layer by extending `libp2p`'s existing QUIC implementation. This transport is designed to utilize SCION's intrinsic multipath capabilities while maintaining compatibility with standard IPFS operations.

### Architecture

The SCION transport operates as a modular component within `libp2p`. It interfaces with the local SCION daemon (dispatcher) to discover and utilize network paths.

#### Path Pinning & Connection Pooling
Standard QUIC congestion control assumes a stable network path. To prevent Round-Trip Time (RTT) disruptions caused by packet-level path switching, our implementation uses **Path Pinning**:

1.  **Discovery:** When initiating communication with a peer, the transport queries the local SCION daemon for available end-to-end paths.
2.  **Connection Pinning:** We establish a distinct QUIC connection for each selected SCION path.
3.  **Connection Pool:** These parallel connections are maintained in a pool for the duration of the session.

### Integration with Bitswap
The transport layer exposes this pool of connections to upper-layer protocols like **Bitswap** (the IPFS data exchange protocol).

*   **Workflow:**
    1.  The Bitswap server queues content requests.
    2.  Worker threads pull tasks and group them into batches (envelopes).
    3.  Envelopes are scheduled concurrently across the available QUIC connections in the pool.
    
This architecture allows IPFS to utilize multiple SCION paths simultaneously for a single logical peer session, significantly increasing resilience and throughput.

### Backward Compatibility
This transport is implemented alongside standard TCP/WebSocket/QUIC-over-IP transports.
*   **SCION-enabled peers** will prefer the `/scion/` transport when available.
*   **Standard peers** continue to communicate over standard IP methods.
*   **Peer Validation:** The transport integrates with the implementation of SCION's Control-Plane PKI (CP-PKI) to ensure that the remote peer is reachable at the claimed SCION address (see Task 2).


## References
*   [Multicodec Registration PR](https://github.com/multiformats/multicodec/pull/325)
*   [go-multiaddr SCION Support](https://github.com/multiformats/go-multiaddr/pull/285)
*   [go-libp2p Current Branch](https://github.com/netsys-lab/go-libp2p/tree/feature/scion-quic-transport)