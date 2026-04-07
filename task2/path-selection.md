


# IPFS over SCION - Path Selection Strategies

This document presents the core ideas how the theoretical multipath routing strategies are cleanly [implemented in the Go codebase](https://github.com/netsys-lab/boxo/tree/feature/scion-boxo).

---

## 1. The Theory: Path Selection in IPFS over SCION

When IPFS is modified to support SCION, `libp2p` establishes multiple parallel QUIC connections to a peer—one for each available SCION path. Because IPFS transfers data in discrete batches called *envelopes* using the **Bitswap** protocol, the system needs an intelligent way to decide *which* path to use for *which* envelope.

We define eight distinct **Path Selection Strategies** to optimize these transfers:
1. **Random:** Assigns paths completely randomly.
2. **Single Shortest (Baseline):** Uses the shortest available path for all transfers (mimicking traditional BGP routing).
3. **First free random:** Selects the first available (unused) path randomly.
4. **First free lowest latency:** Chooses the first free path with the lowest static metadata latency.
5. **First free lowest lat. sub:** Similar to #4, but with a sub-value latency fallback.
6. **First free most disjoint:** Prefers paths with minimal shared network interfaces.
7. **First free shortest:** Selects the shortest available path that is currently not in use.
8. **First free highest bandw.:** Chooses the path with the highest historically estimated bandwidth.


## 2. The Implementation: Refactoring to the Strategy Pattern

In the provided codebase, the Bitswap server (`go-bitswap/server`) is responsible for sending blocks (`sendBlocks`) to peers. Originally, the routing logic was implemented without path selection in mind. 

To bridge this academic research with robust software engineering, the codebase was refactored. The complex branching logic was abstracted into a clean **Strategy Pattern**.

### Step 1: Defining the Interface
A simple, uniform interface was created to encapsulate the decision-making process for picking a path. It takes the available paths, the current path usage, and the historical bandwidth rates, and returns the optimal SCION path.

```go
type PathSelector interface {
	SelectPath(paths []snet.Path, usage map[snet.PathFingerprint]int, rates map[string]float64) snet.Path
}
```

### Step 2: The Factory Method
A factory method was implemented to map the integer configurations (representing the 8 strategies) to their respective implementations. This ensures the `Server` struct doesn't need to know *how* paths are selected, only *that* they are selected.

```go
func getPathSelector(strat int) PathSelector {
	switch strat {
	case completelyRandomStrat:          // Strategy 1
		return CompletelyRandomSelector{}
	case singleShortestPathStrat:        // Strategy 2
		return &SingleShortestPathSelector{}
	case firstFreeRandomStrat:           // Strategy 3
		return FirstFreeRandomSelector{}
	// ...[Other Strategies mapped here]
	case firstFreeHighestBandwidth:      // Strategy 8
		return FirstFreeHighestBandwidthSelector{}
	default:
		return CompletelyRandomSelector{}
	}
}
```

### Step 3: Clean Concrete Implementations
Each strategy now exists as an isolated, easily testable struct. 

For example, the **First Free Highest Bandwidth** strategy is implemented cleanly by filtering paths that have bandwidth telemetry, sorting them by rate, and selecting the highest-rated path that isn't currently saturated:

```go
type FirstFreeHighestBandwidthSelector struct{}

func (s FirstFreeHighestBandwidthSelector) SelectPath(paths []snet.Path, usage map[snet.PathFingerprint]int, rates map[string]float64) snet.Path {
	// Filter paths that have recorded bandwidth rates
	pathsWithBw := filter(paths, func(p snet.Path) bool {
		_, ok := rates[snet.Fingerprint(p).String()]
		return ok
	})

	if len(pathsWithBw) > 0 {
		// Sort by highest historical bandwidth
		sort.Slice(pathsWithBw, func(i, j int) bool {
			return rates[snet.Fingerprint(pathsWithBw[i]).String()] >
				rates[snet.Fingerprint(pathsWithBw[j]).String()]
		})
		// Pick the first free path
		for _, path := range pathsWithBw {
			if u, ok := usage[snet.Fingerprint(path)]; !ok || u == 0 {
				return path
			}
		}
	}

	// Fallback to shortest available path
	return firstFree(sortShortest(paths), usage)
}
```

### Step 4: Streamlining `sendBlocks`
By utilizing the Strategy pattern, the `sendBlocks` function—the hot-path of the IPFS Bitswap protocol—was drastically simplified. It now relies purely on polymorphism to route network traffic securely and efficiently over SCION:

```go
func (bs *Server) sendBlocks(ctx context.Context, env *decision.Envelope) {
    // ... telemetry and setup ...

	paths, err := bs.network.QueryPaths(ctx, env.Peer)
	var fprint snet.PathFingerprint
	
	if err == nil && len(paths) > 0 {
	    // The Strategy Pattern handles all the complex logic defined in the paper!
		chosenPath := bs.pathSelector.SelectPath(paths, bs.pathUsage, bs.counters.AverageRatePerPath)
		fprint = snet.Fingerprint(chosenPath)
		ctx = network.ViaPath(ctx, chosenPath)
	}

	// Record that this path is in use right now
	bs.pathUsage[fprint] += 1
	
	// Send the payload via QUIC over the selected SCION path
	err = bs.network.SendMessage(ctx, env.Peer, env.Message)
	
	// ... cleanup and telemetry ...
}
```

## Conclusion

The integration of SCION into IPFS proves that next-generation path-aware networking is uniquely suited for decentralized, peer-to-peer applications. By refactoring the IPFS Bitswap implementation to use the Strategy Pattern, the codebase perfectly mirrors the theoretical models proposed. 