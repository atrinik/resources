# Released visual catalog

`resources.json` is the only authoritative admission list for replacement
visual resources in this release. Stable resource IDs do not derive from
checkout paths. Each row fixes the bytes, dimensions, media type, source
coordinate, history identity, transformation, attribution, license notice,
and permitted consumers.

The per-consumer allowlists are deterministic projections of the catalog.
Consumers must verify both the resource ID and SHA-256 digest and must not load
anything from `inventory/`, which is intentionally absent from release
archives.
