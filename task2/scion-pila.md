
# IPFS over SCION: Cryptographic Peer Validation with PILA

## Overview

In decentralized networks like IPFS, sybil attacks and routing hijacking pose significant threats. Because standard IPFS runs over the BGP-based Internet, attackers can easily generate thousands of pseudonymous identities to poison Distributed Hash Tables (DHTs) or execute Man-in-the-Middle (MitM) attacks.


By leveraging **PILA (Pervasive Internet-Wide Low-Latency Authentication)**, the system binds a peer's identity to its cryptographically verifiable SCION address. This document explains the theory behind PILA and demonstrates how it was seamlessly integrated into the `go-libp2p` TLS handshake, as shown [here](https://github.com/netsys-lab/go-libp2p/commit/b4c5ab18ee86c222640bf4c1566e6e7fa9ee9e2b).

---

## 1. The Theory: Peer Validation and PILA

PILA authenticates endhosts based on their network addresses rather than domain names. In the SCION architecture, every Autonomous System (AS) is cryptographically registered within its Isolation Domain (ISD) via a Trust Root Configuration (TRC). 

To prove its identity, an IPFS node obtains a PILA certificate chain consisting of:
1. **CA Certificate:** The issuing Certificate Authority.
2. **AS Certificate:** The SCION Autonomous System.
3. **Endhost Certificate:** The IPFS node itself.

When two IPFS nodes connect, they exchange these chains during the TLS handshake. The receiving node verifies the chain against the SCION TRC and confirms that the peer's IP address matches the one in the certificate. 

**Security Impact:** Because generating a valid PILA certificate requires actual control over a legitimate SCION AS address, the cost of creating fake identities skyrockets, effectively neutralizing large-scale Sybil and Eclipse attacks.

---

## 2. The Implementation: Extending libp2p's TLS Handshake

The integration into the `libp2p` SCION/QUIC transport is designed to be highly modular. The authors extended `libp2p`'s native TLS 1.3 handshake to include the PILA certificates *without breaking the existing libp2p peer authentication mechanisms*.

### Step 1: Exposing the Standard TLS Config
First, the `Identity` struct in `p2p/security/tls/crypto.go` was updated to expose the underlying `tls.Config`, allowing the SCION transport to access the node's base private keys.

```go
func (i *Identity) GetConfig() tls.Config {
	return i.config
}
```

### Step 2: Server-Side — Fetching and Presenting the Certificate
When a SCION-enabled IPFS node starts listening for connections, it checks for a PILA service URL (`SCION_PILA_URL`). If available, it automatically generates a Certificate Signing Request (CSR) using its libp2p private key and fetches a verifiable certificate chain from the local SCION AS.

This chain is then appended to the standard TLS configuration so it is presented to any connecting peer:

```go
// Listen listens for new QUIC connections on the passed multiaddr.
func (t *transport) Listen(addr ma.Multiaddr) (tpt.Listener, error) {
	// ... setup and SCION address parsing ...

	var scionCerts[]tls.Certificate
	pilaURL := os.Getenv("SCION_PILA_URL")
	if pilaURL != "" {
		conf := t.identity.GetConfig()
		if len(conf.Certificates) > 0 {
			key := conf.Certificates[0].PrivateKey.(*ecdsa.PrivateKey)
			client := scionpila.NewSCIONPilaClient(pilaURL)
			
			// 1. Create a CSR using the libp2p private key
			csr, err := scionpila.NewCertificateSigningRequest(key)
			if err != nil {
				return nil, err
			}
			
			// 2. Fetch the PILA certificate chain
			certificate, err := client.FetchCertificateFromSigningRequest(udpAddr.String(), csr)
			if err != nil {
				return nil, err
			}
			
			// 3. Convert to a standard TLS certificate
			scionCerts, err = scionpila.CreateTLSCertificate(certificate, key)
			if err != nil {
				return nil, err
			}
		}
	}

	// Dynamically append the PILA certificates to the standard libp2p TLS config
	tlsConf.GetConfigForClient = func(_ *tls.ClientHelloInfo) (*tls.Config, error) {
		conf, _ := t.identity.ConfigForPeer("")
		if len(scionCerts) > 0 {
			conf.Certificates = append(conf.Certificates, scionCerts...)
		}
		return conf, nil
	}
	// ...
}
```

### Step 3: Client-Side — Verifying the Peer
When dialing a peer, the client must verify the server's PILA certificate. To do this without overriding `libp2p`'s native peer ID verification, the codebase employs a clean wrapper function around `VerifyPeerCertificate`. 

If `SCION_PILA_CERTS_FOLDER` is configured, it first runs the SCION TRC verification. If that passes, it delegates the rest of the verification back to the original libp2p function:

```go
func (t *transport) dialWithScope(ctx context.Context, raddr ma.Multiaddr, p peer.ID) (tpt.CapableConn, error) {
	// ... setup ...

	pilaCertsFolder := os.Getenv("SCION_PILA_CERTS_FOLDER")
	if pilaCertsFolder != "" {
		udpAddr, _, err := scionquicreuse.FromQuicMultiaddr(raddr)
		if err != nil {
			return nil, err
		}
		remoteVerifyFunc := scionpila.VerifyQUICCertificateChainsHandler(pilaCertsFolder, udpAddr.String())
		
		// Capture the original libp2p verification function
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
