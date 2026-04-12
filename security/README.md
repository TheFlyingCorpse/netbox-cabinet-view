# Security artifacts

This directory ships the standardised supply-chain documents that compliance frameworks (NIS2, the EU Cyber Resilience Act, NIST SSDF, EO 14028) increasingly ask consumers of OT/ICS software to look for.

## `sbom.cdx.json` — CycloneDX Software Bill of Materials

A [CycloneDX 1.6](https://cyclonedx.org/docs/1.6/json/) JSON document listing every direct and transitive runtime dependency of `netbox-cabinet-view` at the tagged release version, with [PackageURL](https://github.com/package-url/purl-spec) (purl) identifiers for tooling like `grype`, `trivy`, `osv-scanner`, Dependency-Track, and GitHub's dependency graph.

The SBOM is generated reproducibly via:

```bash
# From a clean Python 3.12 venv with the built wheel installed
python -m cyclonedx_py environment <venv>/bin/python \
  --sv 1.6 \
  --of JSON \
  -o security/sbom.cdx.json \
  --pyproject pyproject.toml \
  --mc-type library \
  --output-reproducible
```

### Current contents at v0.7.1

The runtime dependency graph is intentionally tiny — the plugin is packaged as pure Python and only requires one third-party library beyond NetBox itself (which is installed by the user, not as a Python dependency).

| Component | Version | purl |
|---|---|---|
| `netbox-cabinet-view` (this plugin, the root component) | 0.7.1 | `pkg:pypi/netbox-cabinet-view@0.7.1` |
| `svgwrite` | 1.4.3 | `pkg:pypi/svgwrite@1.4.3` |

Run any modern SBOM / vulnerability scanner against the file for a live feed:

```bash
grype sbom:./security/sbom.cdx.json
trivy sbom security/sbom.cdx.json
osv-scanner --sbom=security/sbom.cdx.json
```

## `openvex.json` — OpenVEX Vulnerability Exploitability eXchange

An [OpenVEX 0.2.0](https://openvex.dev/) document that tells consumers which CVEs actually affect the running code, distinct from "my SBOM mentions a component that has a CVE somewhere". Complementary to the SBOM: the SBOM says *what's in the box*, the VEX says *which alerts are relevant*.

The current document contains a single `not_affected` floor statement — at the v0.7.1 release timestamp the maintainer is not aware of any CVE affecting either the plugin or `svgwrite`. As new vulnerabilities are reported and triaged, per-CVE statements will be appended to `statements[]`.

Consumers requiring continuously-updated VEX should subscribe to this repository's [GitHub Security Advisories](https://github.com/TheFlyingCorpse/netbox-cabinet-view/security/advisories).

## Reporting a security issue

Open a private [Security Advisory](https://github.com/TheFlyingCorpse/netbox-cabinet-view/security/advisories) on GitHub. Please do **not** open a public issue for undisclosed vulnerabilities.
