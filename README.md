# SCION-IPFS

The vast amount of content on the Internet has made it increasingly challenging for users to quickly and reliably access relevant information. A key issue in managing and retrieving information in distributed systems is locating data items in a manner that ensures scalability, minimal communication complexity, and high reliability, even in the presence of adversaries. Specifically, determining where to store information so that requesters can easily find it, as well as enabling users to discover and efficiently locate desired data items, are critical challenges. Centralized approaches offer fast data lookup and constant search complexity but may suffer from scalability issues, single points of failure, and trust concerns. As a result, decentralized approaches are more desirable, although they often come with increased communication overhead. Recent solutions, such as the Interplanetary FileSystem (IPFS), address some of these problems but still have limitations in their performance, as discussed in the related efforts section below.

In this project, our objective is to create a secure, reliable, and decentralized storage platform based on IPFS, that outperforms existing approaches in terms of fast, scalable content search and lookup. By leveraging path-awareness, we aim to utilize network resources efficiently to reduce search and lookup delays while enhancing overall throughput.

SCION is a clean-slate Next-Generation Internet (NGI) architecture which offers a.o. multi-path and path-awareness capabilities by design. Moreover, SCION was designed to provide route control, failure isolation, and explicit trust information for end-to-end communication. As a result, the SCION architecture provides strong resilience and security properties as an intrinsic consequence of its design. The goal in this project is to leverage the path-awareness in SCION to align the storage and lookup in IPFS with the underlying network in an optimal manner, while at the same time using SCION to establish trust between the entities.

While the SCION network offers a set of potential paths between two end hosts, it’s up to the application to select the optimal ones considering performance requirements in terms of delay or throughput, and potentially combining them into a multi-path connection. The primary result will be a libp2p transport library as well as an IPFS version that enables IPFS nodes to communicate over SCION. This will provide demonstrable improvements in performance and security against common routing-based attacks. The project will culminate in a comprehensive evaluation across emulated and real-world production networks, a security analysis, and the release of a well-documented library for developers.

## Task 1. Native SCION Support in libp2p for IPFS

This task covers the foundational work of integrating [SCION into the core networking layer of IPFS, libp2p](task1/implementation.md). This involves creating a new multipath-capable transport that allows IPFS peers to establish connections and transfer data over SCION paths.


### Milestones
- [x] [Definition and implementation of a SCION multiaddr format for peer addressing](https://github.com/multiformats/go-multiaddr/pull/285).
- [x] [A working multipath transport for SCION based on the QUIC protocol within libp2p](https://github.com/netsys-lab/go-libp2p/tree/feature/scion-quic-transport).


## Task 2. Advanced Path Selection and Peer Verification

This task focuses on implementing the intelligence and security features of the integration. It includes developing strategies to efficiently distribute traffic across multiple SCION paths and integrating strong cryptographic peer identity verification.

### Milestones
- [x] [Implementation of adaptive, bandwidth-aware path selection strategies to optimize performance](task2/path-selection.md)
- [x] [Integration of cryptographic peer verification using SCION's Control-Plane Public Key Infrastructure (CP-PKI)](task2/scion-pila.md)

## Task 3. Security Analysis and Hardening

This task involves a comprehensive security analysis to verify the implementation's resilience against critical attack vectors that affect traditional P2P systems.

### Milestones

- [x] [Qualitative analysis of the implementation's resilience against Man-in-the-Middle (MitM), Sybil, and BGP hijacking attacks](task3/security-analysis.md). We will onboard help from ROS provided security audit.
- [x] [A simulation](task3/simulation-framework.md) and [detailed report](task3/report.md) quantifying the effectiveness of SCION-based peer validation in mitigating large-scale Sybil attacks. 

## Task 4. Performance Evaluation and Demonstration

This task consists of a thorough evaluation of the performance benefits of running IPFS over SCION. The work will be concluded by packaging the implementation into a reusable library with full documentation for third-party developers.

### Milestones
- [x] [Comparative performance analysis](task4/performance-report.md) of content retrieval times in both emulated and real-world testbed (e.g., SCIONLab) environments.
- [x] [Release 1.0 of the IPFS-over-SCION libp2p library](https://github.com/netsys-lab/scion-ipfs/releases/tag/v1.0.0).
- [x] [Comprehensive developer documentation](task4/developer-documentation.md) and a [final performance report](task4/final-performance-report.md).
