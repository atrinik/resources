"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

async function main() {
  const cwd = path.resolve(__dirname, "../..");
  const config = JSON.parse(fs.readFileSync(path.join(cwd, ".releaserc.json"), "utf8"));
  const [plugin, options] = config.plugins.find(
    ([name]) => name === "@semantic-release/release-notes-generator",
  );
  const {generateNotes} = await import(plugin);
  // Call only the real notes hook: no GitHub credentials, tags, or publication.
  const notes = await generateNotes(options, {
    cwd,
    env: {},
    logger: {log() {}},
    options: {repositoryUrl: "https://github.com/atrinik/resources.git"},
    lastRelease: {gitTag: "v1.0.0"},
    nextRelease: {version: "2.0.0", gitTag: "v2.0.0"},
    commits: [
      {hash: "a".repeat(40), message: "fix: preserve resource checksums (#42)"},
      {hash: "b".repeat(40), message: "feat: add resource catalog"},
      {
        hash: "c".repeat(40),
        message: "feat!: update catalog schema\n\nBREAKING CHANGE: consumers must read schema two",
      },
    ],
  });
  assert.match(notes, /Bug Fixes/);
  assert.match(notes, /preserve resource checksums/);
  assert.match(notes, /Features/);
  assert.match(notes, /add resource catalog/);
  assert.match(notes, /BREAKING CHANGES/);
  assert.match(notes, /consumers must read schema two/);
  const links = Array.from(notes.matchAll(/\]\(([^)]+)\)/g), (match) => match[1]);
  assert.ok(links.includes("https://github.com/atrinik/resources/issues/42"));
  assert.ok(links.includes("https://github.com/atrinik/resources/compare/v1.0.0...v2.0.0"));
  console.log("release notes: configured plugin rendered fixes, features, breaking changes and links");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
