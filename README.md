# Atrinik server resources

This repository owns the separately released media resources consumed by the
Atrinik server. Server source and container/package assembly live in
[`atrinik/server`](https://github.com/atrinik/server), which pins this
repository's release archive instead of using a Git submodule.

## Licensing and attribution

Resource licensing is asset-specific. The paintings and their terms are kept
together under `paintings/`; see `paintings/LICENSE`. Preserve that notice and
any nearby attribution when adding or replacing resources. This repository
does not apply a new blanket license to those assets.

[`catalog/resources.json`](catalog/resources.json) is the fail-closed release
catalog. It assigns stable IDs and records immutable content hashes,
dimensions, media types, source coordinates, authorship evidence,
transformations, license notices, and permitted consumers. Consumer-specific
allowlists in `catalog/allowlists/` are deterministic projections of that
catalog; consumers verify both ID and digest.

`inventory/` records candidate visuals from pinned complete-history classic
and content checkouts. Inventory rows are not approvals and are never shipped.
All have empty consumer lists and an excluded or blocked decision. In
particular, the 526 content visuals without a matching legacy declaration stay
blocked until their provenance is resolved. Rebuild and compare the inventory
with:

```sh
tools/resource-inventory.py generate \
  --classic-root /path/to/classic \
  --content-root /path/to/content
tools/resource-inventory.py validate \
  --classic-root /path/to/classic \
  --content-root /path/to/content
```

`runtime-paths.txt` is the allowlist of tracked assets and release-catalog
paths distributed to consumers.
Add each new top-level asset collection there; repository documentation,
release tooling, untracked files, and other development metadata are not game
resources and must not be exposed through the server's asset protocol.

## Releases

Every squash merge uses its Conventional Commits pull-request title to create
at least a patch release. Each release publishes a deterministic
`atrinik-resources-VERSION.tar.gz` archive and `SHA256SUMS`; consumers pin the
tag, source commit, asset URL, and SHA-256 digest.

Validation runs directly on `ubuntu-24.04` and installs actionlint 1.7.9 from
its SHA-256-pinned upstream archive. Release automation uses the immutable
GitHub-owned setup-node v7 action with Node 24.18.1; it does not depend on a
private organization container package.
