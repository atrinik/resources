# Atrinik resources repository guide

- This repository owns separately released server media resources. Server code,
  runtime assembly, and container packaging remain in the server repository.
- `runtime-paths.txt` is the distribution boundary. Release archives may contain
  only non-executable tracked regular files under its allowlisted asset and
  catalog paths; do not package candidate inventories, repository metadata,
  tooling, untracked files, or links.
- `catalog/resources.json` is the sole admission source. Keep its stable IDs,
  hashes, dimensions, source/history evidence, transformations, narrow license
  notices, and consumer permissions synchronized with the actual bytes. Treat
  `catalog/allowlists/` as generated projections and every `inventory/` row as
  blocked or excluded, never as a packaging input.
- Regenerate candidate inventories only from complete, non-shallow classic and
  content checkouts at the exact pinned revisions. Applying an approved MIT
  provenance grant still requires the workspace guide's complete-history,
  sole-authorship, originality, and third-party review; a legacy attribution
  declaration alone is not approval.
- Preserve portable case-correct paths, stable runtime references, provenance,
  attribution, and the narrowest applicable per-asset license.
- Keep release archives and `SHA256SUMS` deterministic. Consumers use immutable
  checksum-pinned releases rather than Git submodules.
- Run `tools/validate.sh` and the source-backed inventory validation. They check
  Python compilation, catalog projections, candidate exclusions, ShellCheck,
  actionlint, deterministic archives, checksums, notices, and the absence of
  excluded development paths.
- Commits and pull-request titles use Conventional Commits. Every squash merge
  is released by semantic-release.
- Keep package output under `build/`, preserve unrelated work, and finish with
  `git diff --check`.
- Update this `AGENTS.md` in the same change when major rework alters resource
  ownership, the runtime allowlist, packaging, licensing, or validation.
