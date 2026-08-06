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

`runtime-paths.txt` is the allowlist of tracked paths distributed to servers.
Add each new top-level asset collection there; repository documentation,
release tooling, untracked files, and other development metadata are not game
resources and must not be exposed through the server's asset protocol.

## Releases

Every squash merge uses its Conventional Commits pull-request title to create
at least a patch release. Each release publishes a deterministic
`atrinik-resources-VERSION.tar.gz` archive and `SHA256SUMS`; consumers pin the
tag, source commit, asset URL, and SHA-256 digest.
