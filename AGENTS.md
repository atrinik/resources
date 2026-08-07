# Atrinik resources repository guide

- This repository owns separately released server media resources. Server code,
  runtime assembly, and container packaging remain in the server repository.
- `runtime-paths.txt` is the distribution boundary. Release archives may contain
  only tracked regular files under its allowlisted asset roots; do not package
  repository metadata, tooling, untracked files, or links.
- Preserve portable case-correct paths, stable runtime references, provenance,
  attribution, and the narrowest applicable per-asset license.
- Keep release archives and `SHA256SUMS` deterministic. Consumers use immutable
  checksum-pinned releases rather than Git submodules.
- Validate shell syntax for `tools/package-release.sh`, required license files,
  the allowlist, a locally built release archive, its checksum, and that no
  excluded development path appears in the archive.
- Commits and pull-request titles use Conventional Commits. Every squash merge
  is released by semantic-release.
- Keep package output under `build/`, preserve unrelated work, and finish with
  `git diff --check`.
- Update this `AGENTS.md` in the same change when major rework alters resource
  ownership, the runtime allowlist, packaging, licensing, or validation.
