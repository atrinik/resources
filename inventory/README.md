# Visual candidate inventory

These JSON Lines snapshots are evidence inventories, not distribution
allowlists. Every row is fail-closed: it has no permitted consumer and has an
`excluded_` or `blocked_` decision. Only resources in
`catalog/resources.json` may enter a release.

The snapshots cover every PNG at these immutable coordinates:

- `atrinik/classic@49304ea3ba2507e1ee3380652a90c2c6c5af709b`, under
  `client/textures/` (125 candidates);
- `atrinik/content@01b1fdb65c2243df4bafe9c8109fc93229df0121`
  (9,413 candidates).

The content inventory preserves the nearest legacy attribution declaration as
evidence, but does not treat that declaration as replacement-use approval.
Exactly 526 content rows have no matching declaration and remain
`blocked_missing_license`. The other rows and every classic-client row remain
excluded until their authorship, originality, source, derivative chain,
license compatibility, and notice have been independently reviewed.

Regenerate only from complete, non-shallow checkouts at the pinned revisions:

```sh
tools/resource-inventory.py generate \
  --classic-root /path/to/classic \
  --content-root /path/to/content
```
