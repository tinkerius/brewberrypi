# Image signing

Release images are signed with a cosign key pair (ADR-0001, runtime contract §1). BrewberryPi OS accepts
only images whose signature matches the pinned public key.

| File | Purpose |
|---|---|
| `cosign.pub` | Public key. Committed here and baked into BrewberryPi OS (`tinkerius/brewberrypi-os`). |
| `policy.json`, `registries.d/` | The same verification policy as on the device. CI uses it as a release gate (`skopeo copy` must accept the freshly signed image). |

The private key and its password are **never** committed. They live only in the GitHub Actions
secrets `COSIGN_PRIVATE_KEY` and `COSIGN_PASSWORD`, and in a password manager as a backup.

## Rules

- **Use cosign v2.x.** Podman 5.4 (Debian Trixie) reads only the legacy signature tag format `sha256-<digest>.sig`; cosign v3's default format is rejected.
- **Sign with `--tlog-upload=false`.** The registry is private, so no entries go to the public Rekor transparency log.

## Creating the key pair (once)

```bash
cd deploy/signing
docker run --rm -it -v "$PWD:/keys" -w /keys gcr.io/projectsigstore/cosign:v2.5.0 generate-key-pair
gh secret set COSIGN_PRIVATE_KEY -R tinkerius/brewberrypi < cosign.key
gh secret set COSIGN_PASSWORD -R tinkerius/brewberrypi        # paste the password
# store cosign.key and the password in your password manager, then:
shred -u cosign.key
git add cosign.pub
```
