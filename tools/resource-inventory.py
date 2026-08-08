#!/usr/bin/env python3
"""Generate and validate the fail-closed visual resource catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import struct
import subprocess
import sys
import tempfile
from typing import Any


CLASSIC_REPOSITORY = "atrinik/classic"
CLASSIC_REVISION = "49304ea3ba2507e1ee3380652a90c2c6c5af709b"
CONTENT_REPOSITORY = "atrinik/content"
CONTENT_REVISION = "01b1fdb65c2243df4bafe9c8109fc93229df0121"
RESOURCE_REPOSITORY = "atrinik/resources"
PAINTING_ORIGINAL_REVISION = "f9c0850b7deabacb3cc14875256caac9fb90ab64"
PAINTING_CONVERSION_REVISION = "d629f89f1ae4cbffdfd201009ae1b1821c8c3f1f"
PAINTING_AUTHOR = {
    "name": "Alex Tokar",
    "email": "admin@atokar.net",
}
PAINTING_NAMES = (
    "canopy.jpg",
    "cave_entrance.jpg",
    "forest.jpg",
    "hill.jpg",
    "hill2.jpg",
    "lake.jpg",
    "moon.jpg",
    "ruins.jpg",
    "waterfall.jpg",
    "wolf.jpg",
)
ORIGINAL_JPEGS = {"cave_entrance.jpg", "hill2.jpg"}
MAX_RESOURCE_BYTES = 64 * 1024 * 1024
MAX_DIMENSION = 8192
EXPECTED_CONTENT_VISUALS = 9413
EXPECTED_CONTENT_UNMATCHED = 526
EXPECTED_CLASSIC_VISUALS = 125


class InventoryError(RuntimeError):
    """Raised when resource evidence does not satisfy the catalog contract."""


def run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *arguments),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def git_bytes(root: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ("git", "-C", str(root), "show", f"{revision}:{path}"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def require_source(root: Path, revision: str) -> None:
    if run_git(root, "rev-parse", "HEAD").strip() != revision:
        raise InventoryError(f"{root} is not at pinned revision {revision}")
    if run_git(root, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise InventoryError(f"{root} must have complete Git history")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def dimensions(path: Path) -> tuple[int, int, str]:
    with path.open("rb") as stream:
        signature = stream.read(24)
        if signature.startswith(b"\x89PNG\r\n\x1a\n"):
            if signature[12:16] != b"IHDR":
                raise InventoryError(f"invalid PNG header: {path}")
            width, height = struct.unpack(">II", signature[16:24])
            return width, height, "image/png"

        if signature[:2] != b"\xff\xd8":
            raise InventoryError(f"unsupported visual format: {path}")
        stream.seek(2)
        while True:
            byte = stream.read(1)
            while byte == b"\xff":
                byte = stream.read(1)
            if not byte:
                break
            marker = byte[0]
            if marker in {0x01, *range(0xD0, 0xDA)}:
                continue
            length_bytes = stream.read(2)
            if len(length_bytes) != 2:
                break
            length = struct.unpack(">H", length_bytes)[0]
            if length < 2:
                break
            if marker in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                frame = stream.read(length - 2)
                if len(frame) < 5:
                    break
                height, width = struct.unpack(">HH", frame[1:5])
                return width, height, "image/jpeg"
            stream.seek(length - 2, os.SEEK_CUR)
    raise InventoryError(f"invalid JPEG structure: {path}")


def visual_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise InventoryError(f"visual must be a regular non-link file: {path}")
    size = path.stat().st_size
    width, height, media_type = dimensions(path)
    if size <= 0 or size > MAX_RESOURCE_BYTES:
        raise InventoryError(f"visual byte bound exceeded: {path}")
    if not 0 < width <= MAX_DIMENSION or not 0 < height <= MAX_DIMENSION:
        raise InventoryError(f"visual dimension bound exceeded: {path}")
    return {
        "sha256": digest(path),
        "size_bytes": size,
        "width": width,
        "height": height,
        "media_type": media_type,
    }


def source_history(root: Path, revision: str, prefix: str) -> dict[str, list[dict[str, str]]]:
    output = run_git(
        root,
        "log",
        "--format=@@%H%x1f%aN%x1f%aE",
        "--name-only",
        "--no-renames",
        revision,
        "--",
        prefix,
    )
    history: dict[str, list[dict[str, str]]] = {}
    current: dict[str, str] | None = None
    for line in output.splitlines():
        if line.startswith("@@"):
            commit, name, email = line[2:].split("\x1f")
            current = {"revision": commit, "name": name, "email": email}
        elif line and current is not None:
            records = history.setdefault(line, [])
            if current not in records:
                records.append(current.copy())
    return history


def path_history(root: Path, revision: str, path: str) -> list[dict[str, str]]:
    output = run_git(
        root,
        "log",
        "--follow",
        "--format=%H%x1f%aN%x1f%aE",
        revision,
        "--",
        path,
    )
    records = []
    for line in output.splitlines():
        if not line:
            continue
        commit, name, email = line.split("\x1f")
        records.append({"revision": commit, "name": name, "email": email, "path": path})
    return records


def declared_content_licenses(root: Path) -> dict[str, dict[str, str]]:
    declarations: dict[str, list[dict[str, str]]] = {}
    for notice in sorted(root.rglob("LICENSE")):
        if not any(notice.parent.rglob("*.png")):
            continue
        lines = notice.read_text(encoding="utf-8").splitlines()
        nonempty = [line for line in lines if line.strip()]
        if len(nonempty) == 1 and not nonempty[0][:1].isspace() and not nonempty[0].endswith(":"):
            for path in sorted(notice.parent.rglob("*.png")):
                relative = path.relative_to(root).as_posix()
                declarations.setdefault(relative, []).append(
                    {
                        "declared_attribution": nonempty[0],
                        "declared_license": license_from_heading(nonempty[0]),
                        "declared_entry_note": None,
                        "notice_path": notice.relative_to(root).as_posix(),
                    }
                )
            continue
        heading: str | None = None
        for number, raw_line in enumerate(lines, 1):
            if not raw_line.strip():
                continue
            if raw_line[:1].isspace():
                if heading is None:
                    raise InventoryError(f"entry before heading: {notice}:{number}")
                token = raw_line.strip().split()[0]
                entry_note = raw_line.strip()[len(token):].strip() or None
                target = notice.parent / token
                if not target.exists():
                    raise InventoryError(f"missing license target: {notice}:{number}: {token}")
                paths = (
                    sorted(target.rglob("*.png"))
                    if target.is_dir()
                    else [target]
                )
                for path in paths:
                    if path.suffix != ".png":
                        continue
                    relative = path.relative_to(root).as_posix()
                    declarations.setdefault(relative, []).append(
                        {
                            "declared_attribution": heading,
                            "declared_license": license_from_heading(heading),
                            "declared_entry_note": entry_note,
                            "notice_path": notice.relative_to(root).as_posix(),
                        }
                    )
            elif raw_line.endswith(":"):
                heading = raw_line[:-1]
            else:
                raise InventoryError(f"invalid license line: {notice}:{number}")

    selected: dict[str, dict[str, str]] = {}
    for path, candidates in declarations.items():
        candidates.sort(key=lambda item: item["notice_path"].count("/"), reverse=True)
        most_specific = candidates[0]
        same_depth = [
            candidate
            for candidate in candidates
            if candidate["notice_path"].count("/")
            == most_specific["notice_path"].count("/")
        ]
        if len({tuple(candidate.items()) for candidate in same_depth}) != 1:
            raise InventoryError(f"ambiguous license declarations for {path}")
        selected[path] = most_specific
    return selected


def license_from_heading(heading: str) -> str:
    normalized = heading.upper().replace("_", "-")
    for token, identifier in (
        ("CC-BY-SA 3.0", "CC-BY-SA-3.0"),
        ("CC BY-SA 3.0", "CC-BY-SA-3.0"),
        ("CC-BY 3.0", "CC-BY-3.0"),
        ("CC BY 3.0", "CC-BY-3.0"),
        ("CC0", "CC0-1.0"),
        ("GPLV3", "LicenseRef-legacy-GPLv3"),
        ("GPLV2", "LicenseRef-legacy-GPLv2"),
        ("GPL", "LicenseRef-legacy-GPL-unspecified"),
        ("PUBLIC DOMAIN", "LicenseRef-legacy-Public-Domain"),
        ("FREEWARE", "LicenseRef-legacy-Freeware"),
    ):
        if token in normalized:
            return identifier
    return "LicenseRef-legacy-Unparsed"


def candidate_record(
    repository: str,
    revision: str,
    root: Path,
    path: str,
    history: dict[str, list[dict[str, str]]],
    declaration: dict[str, str] | None,
) -> dict[str, Any]:
    metadata = visual_metadata(root / path)
    unmatched = declaration is None
    namespace = "classic-client" if repository == CLASSIC_REPOSITORY else "content"
    return {
        "candidate_id": f"candidate:{namespace}:{path}",
        "repository": repository,
        "revision": revision,
        "path": path,
        **metadata,
        "history": history.get(path, []),
        "declared_attribution": None if unmatched else declaration["declared_attribution"],
        "declared_license": None if unmatched else declaration["declared_license"],
        "declared_entry_note": None if unmatched else declaration["declared_entry_note"],
        "notice_path": None if unmatched else declaration["notice_path"],
        "derivative_base_chain": [],
        "transformations": [],
        "permitted_consumers": [],
        "decision": "blocked_missing_license" if unmatched else "excluded_pending_provenance_review",
        "provenance_gaps": (
            [
                "author",
                "source",
                "license",
                "attribution",
                "derivative_base_chain",
                "transformations",
            ]
            if unmatched
            else [
                "complete_history_originality_review",
                "source_chain_review",
                "derivative_chain_review",
                "license_compatibility_review",
            ]
        ),
    }


def painting_catalog(repository_root: Path) -> dict[str, Any]:
    records = []
    for name in PAINTING_NAMES:
        path = repository_root / "paintings" / name
        source_revision = (
            PAINTING_ORIGINAL_REVISION if name in ORIGINAL_JPEGS else PAINTING_CONVERSION_REVISION
        )
        transformations = [] if name in ORIGINAL_JPEGS else ["lossy PNG-to-JPEG conversion"]
        base_chain = []
        jpeg_path = f"paintings/{name}"
        history = path_history(repository_root, "HEAD", jpeg_path)
        expected_history_revisions = [source_revision]
        if name not in ORIGINAL_JPEGS:
            original_path = f"paintings/{Path(name).stem}.png"
            original_bytes = git_bytes(repository_root, PAINTING_ORIGINAL_REVISION, original_path)
            base_chain = [
                {
                    "repository": RESOURCE_REPOSITORY,
                    "revision": PAINTING_ORIGINAL_REVISION,
                    "path": original_path,
                    "sha256": hashlib.sha256(original_bytes).hexdigest(),
                }
            ]
            history.extend(path_history(repository_root, PAINTING_ORIGINAL_REVISION, original_path))
            expected_history_revisions.append(PAINTING_ORIGINAL_REVISION)
        if [record["revision"] for record in history] != expected_history_revisions:
            raise InventoryError(f"painting history changed and requires review: {name}")
        if any(
            record["name"] != PAINTING_AUTHOR["name"]
            or record["email"] != PAINTING_AUTHOR["email"]
            for record in history
        ):
            raise InventoryError(f"painting author identity changed and requires review: {name}")
        records.append(
            {
                "resource_id": f"atrinik:painting:{Path(name).stem}",
                "path": f"paintings/{name}",
                **visual_metadata(path),
                "source": {
                    "repository": RESOURCE_REPOSITORY,
                    "revision": source_revision,
                    "path": jpeg_path,
                    "authors": [PAINTING_AUTHOR],
                },
                "provenance_class": "compatible_third_party",
                "complete_history": history,
                "license": "CC-BY-SA-3.0",
                "attribution": 'Alex "Cleo" Tokar',
                "notice_path": "paintings/LICENSE",
                "notice_sha256": digest(repository_root / "paintings" / "LICENSE"),
                "dependencies": [],
                "derivative_base_chain": base_chain,
                "transformations": transformations,
                "permitted_consumers": [
                    "client-package",
                    "editor-reference",
                    "renderer-test",
                    "server-stream",
                    "website",
                ],
            }
        )
    return {
        "schema_version": 1,
        "catalog": "atrinik-replacement-visual-resources",
        "bounds": {
            "maximum_file_bytes": MAX_RESOURCE_BYTES,
            "maximum_dimension": MAX_DIMENSION,
        },
        "resources": records,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_json_lines(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def generate(
    repository_root: Path,
    classic_root: Path,
    content_root: Path,
    output_root: Path | None = None,
) -> None:
    output_root = repository_root if output_root is None else output_root
    require_source(classic_root, CLASSIC_REVISION)
    require_source(content_root, CONTENT_REVISION)
    classic_paths = sorted(
        path.relative_to(classic_root).as_posix()
        for path in (classic_root / "client" / "textures").rglob("*.png")
    )
    content_paths = sorted(
        path.relative_to(content_root).as_posix()
        for path in content_root.rglob("*.png")
    )
    if len(classic_paths) != EXPECTED_CLASSIC_VISUALS:
        raise InventoryError("classic visual count changed")
    if len(content_paths) != EXPECTED_CONTENT_VISUALS:
        raise InventoryError("content visual count changed")

    classic_history = source_history(classic_root, CLASSIC_REVISION, "client/textures")
    content_history = source_history(content_root, CONTENT_REVISION, ".")
    content_licenses = declared_content_licenses(content_root)
    classic_records = [
        candidate_record(
            CLASSIC_REPOSITORY,
            CLASSIC_REVISION,
            classic_root,
            path,
            classic_history,
            None,
        )
        for path in classic_paths
    ]
    content_records = [
        candidate_record(
            CONTENT_REPOSITORY,
            CONTENT_REVISION,
            content_root,
            path,
            content_history,
            content_licenses.get(path),
        )
        for path in content_paths
    ]
    unmatched = sum(record["decision"] == "blocked_missing_license" for record in content_records)
    if unmatched != EXPECTED_CONTENT_UNMATCHED:
        raise InventoryError(f"expected {EXPECTED_CONTENT_UNMATCHED} unmatched content visuals, got {unmatched}")

    catalog = painting_catalog(repository_root)
    write_json(output_root / "catalog" / "resources.json", catalog)
    consumers = sorted(
        {
            consumer
            for resource in catalog["resources"]
            for consumer in resource["permitted_consumers"]
        }
    )
    for consumer in consumers:
        write_json(
            output_root / "catalog" / "allowlists" / f"{consumer}.json",
            {
                "schema_version": 1,
                "consumer": consumer,
                "resources": [
                    {"resource_id": resource["resource_id"], "sha256": resource["sha256"]}
                    for resource in catalog["resources"]
                    if consumer in resource["permitted_consumers"]
                ],
            },
        )
    write_json_lines(output_root / "inventory" / "classic-client-visuals.jsonl", classic_records)
    write_json_lines(output_root / "inventory" / "content-visuals.jsonl", content_records)


def load_json_lines(path: Path) -> list[dict[str, Any]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise InventoryError(f"invalid JSON at {path}:{number}: {error}") from error
        if not isinstance(value, dict):
            raise InventoryError(f"inventory row is not an object: {path}:{number}")
        records.append(value)
    return records


def validate_snapshot(repository_root: Path) -> None:
    catalog_path = repository_root / "catalog" / "resources.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    expected_catalog = painting_catalog(repository_root)
    if catalog != expected_catalog:
        raise InventoryError("catalog/resources.json is stale; run generate")
    resources = catalog.get("resources", [])
    ids = [resource["resource_id"] for resource in resources]
    paths = [resource["path"] for resource in resources]
    if len(resources) != len(PAINTING_NAMES) or len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise InventoryError("catalog resource IDs and paths must be complete and unique")
    for resource in resources:
        notice = repository_root / resource["notice_path"]
        if not notice.is_file() or notice.is_symlink() or not notice.read_text(encoding="utf-8").strip():
            raise InventoryError(f"missing actual notice for {resource['resource_id']}")
        if not resource["permitted_consumers"]:
            raise InventoryError(f"admitted resource has no consumer: {resource['resource_id']}")

    consumers = {
        consumer
        for resource in resources
        for consumer in resource["permitted_consumers"]
    }
    allowlist_paths = sorted((repository_root / "catalog" / "allowlists").glob("*.json"))
    if {path.stem for path in allowlist_paths} != consumers:
        raise InventoryError("consumer allowlist set does not match the catalog")
    for consumer_path in allowlist_paths:
        consumer = consumer_path.stem
        expected = {
            "schema_version": 1,
            "consumer": consumer,
            "resources": [
                {"resource_id": resource["resource_id"], "sha256": resource["sha256"]}
                for resource in resources
                if consumer in resource["permitted_consumers"]
            ],
        }
        if json.loads(consumer_path.read_text(encoding="utf-8")) != expected:
            raise InventoryError(f"stale consumer allowlist: {consumer_path}")

    classic = load_json_lines(repository_root / "inventory" / "classic-client-visuals.jsonl")
    content = load_json_lines(repository_root / "inventory" / "content-visuals.jsonl")
    if len(classic) != EXPECTED_CLASSIC_VISUALS or len(content) != EXPECTED_CONTENT_VISUALS:
        raise InventoryError("candidate inventory count changed")
    if sum(row["decision"] == "blocked_missing_license" for row in content) != EXPECTED_CONTENT_UNMATCHED:
        raise InventoryError("unmatched content exclusion count changed")
    for expected_repository, expected_revision, rows in (
        (CLASSIC_REPOSITORY, CLASSIC_REVISION, classic),
        (CONTENT_REPOSITORY, CONTENT_REVISION, content),
    ):
        identifiers: set[str] = set()
        source_paths: set[str] = set()
        for row in rows:
            identifier = row.get("candidate_id")
            path = row.get("path")
            if not isinstance(identifier, str) or identifier in identifiers:
                raise InventoryError("candidate IDs must be unique strings")
            if not isinstance(path, str) or path in source_paths or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
                raise InventoryError("candidate paths must be unique and safe")
            identifiers.add(identifier)
            source_paths.add(path)
            if row.get("repository") != expected_repository or row.get("revision") != expected_revision:
                raise InventoryError(f"candidate source coordinate drift: {identifier}")
            if row.get("permitted_consumers") or not str(row.get("decision", "")).startswith(("blocked_", "excluded_")):
                raise InventoryError(f"candidate was accidentally admitted: {identifier}")
            if not isinstance(row.get("sha256"), str) or len(row["sha256"]) != 64:
                raise InventoryError(f"candidate digest is invalid: {identifier}")
            if not isinstance(row.get("history"), list) or not row["history"]:
                raise InventoryError(f"candidate history evidence is missing: {identifier}")
            if row.get("media_type") != "image/png":
                raise InventoryError(f"candidate is not a PNG visual: {identifier}")
            if not 0 < row.get("size_bytes", 0) <= MAX_RESOURCE_BYTES:
                raise InventoryError(f"candidate byte bound is invalid: {identifier}")
            if not 0 < row.get("width", 0) <= MAX_DIMENSION or not 0 < row.get("height", 0) <= MAX_DIMENSION:
                raise InventoryError(f"candidate dimension bound is invalid: {identifier}")
            if row["decision"] == "blocked_missing_license":
                if any(row.get(field) is not None for field in ("declared_attribution", "declared_license", "notice_path")):
                    raise InventoryError(f"unmatched candidate has a license declaration: {identifier}")
            elif not all(isinstance(row.get(field), str) for field in ("declared_attribution", "declared_license", "notice_path")):
                raise InventoryError(f"excluded candidate lacks its legacy declaration: {identifier}")


def validate_sources(repository_root: Path, classic_root: Path, content_root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="atrinik-resource-inventory-", dir="/tmp") as directory:
        generated = Path(directory)
        generate(repository_root, classic_root, content_root, generated)
        for relative_root in ("catalog", "inventory"):
            actual_paths = {
                path.relative_to(repository_root)
                for path in (repository_root / relative_root).rglob("*")
                if path.is_file()
            }
            generated_paths = {
                path.relative_to(generated)
                for path in (generated / relative_root).rglob("*")
                if path.is_file()
            }
            # README files explain the contract but are not generated evidence.
            actual_paths.discard(Path(relative_root) / "README.md")
            if actual_paths != generated_paths:
                raise InventoryError(f"generated {relative_root} file set differs from the snapshot")
            for relative in actual_paths:
                if digest(repository_root / relative) != digest(generated / relative):
                    raise InventoryError(f"source checkout evidence differs: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--classic-root", type=Path, required=True)
    generate_parser.add_argument("--content-root", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--classic-root", type=Path)
    validate_parser.add_argument("--content-root", type=Path)
    arguments = parser.parse_args()
    repository_root = Path(run_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    try:
        if arguments.command == "generate":
            generate(repository_root, arguments.classic_root.resolve(), arguments.content_root.resolve())
        else:
            validate_snapshot(repository_root)
            if (arguments.classic_root is None) != (arguments.content_root is None):
                raise InventoryError("both source roots are required for source validation")
            if arguments.classic_root is not None:
                validate_sources(
                    repository_root,
                    arguments.classic_root.resolve(),
                    arguments.content_root.resolve(),
                )
    except (InventoryError, OSError, subprocess.CalledProcessError, KeyError, ValueError) as error:
        print(f"resource inventory error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
