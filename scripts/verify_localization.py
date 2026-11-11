"""Verify the deployable visual resource bundle without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def resource(root, name):
    require(isinstance(name, str) and bool(name), "invalid resource path")
    path = (root / name).resolve()
    require(path.is_relative_to(root), f"resource escapes bundle: {name}")
    return path


def image_size(path):
    with path.open("rb") as stream:
        header = stream.read(30)
    if header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
        return struct.unpack(">II", header[16:24])
    require(len(header) >= 25 and header[:4] == b"RIFF" and header[8:12] == b"WEBP",
            f"invalid PNG/WebP header: {path}")
    require(struct.unpack("<I", header[4:8])[0] + 8 == path.stat().st_size,
            f"truncated WebP container: {path}")
    kind, chunk_size = header[12:16], struct.unpack("<I", header[16:20])[0]
    require(20 + chunk_size + (chunk_size & 1) <= path.stat().st_size,
            f"invalid WebP chunk size: {path}")
    if kind == b"VP8X" and chunk_size == 10 and len(header) >= 30:
        return 1 + int.from_bytes(header[24:27], "little"), 1 + int.from_bytes(header[27:30], "little")
    if kind == b"VP8L" and chunk_size >= 5 and header[20] == 0x2f:
        bits = int.from_bytes(header[21:25], "little")
        return 1 + (bits & 0x3fff), 1 + ((bits >> 14) & 0x3fff)
    if kind == b"VP8 " and chunk_size >= 10 and len(header) >= 30 and header[23:26] == b"\x9d\x01\x2a":
        width, height = struct.unpack("<HH", header[26:30])
        size = width & 0x3fff, height & 0x3fff
        require(all(size), f"empty WebP image: {path}")
        return size
    raise ValueError(f"unsupported WebP image header: {path}")


def matrix(raw):
    require(isinstance(raw, list) and len(raw) == 2, "matrix must have two rows")
    require(all(isinstance(row, list) and len(row) == 3 for row in raw),
            "matrix rows must have three columns")
    require(all(type(v) in (int, float) and math.isfinite(v) for row in raw for v in row),
            "matrix must contain finite numbers")
    return [*raw, [0, 0, 1]]


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["schema_version"] == 1, "unsupported manifest version")
    require(manifest["kind"] == "okef-visual-localization", "unexpected bundle kind")
    declared = set()
    total = 0
    for item in manifest["files"]:
        name = item["path"]
        require(name not in declared, f"duplicate resource: {name}")
        declared.add(name)
        path = resource(root, name)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            first = stream.read(1024 * 1024)
            require(not first.startswith(b"version https://git-lfs.github.com/spec/v1"),
                    f"Git LFS pointer remains: {name}; run git lfs pull")
            digest.update(first)
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        require(path.stat().st_size == item["size"], f"size mismatch: {name}")
        require(digest.hexdigest() == item["sha256"], f"SHA-256 mismatch: {name}")
        total += item["size"]

    referenced = {manifest["layer_catalog"]}
    maps = set()
    for entry in manifest["base_maps"]:
        mid = entry["map_id"]
        require(mid not in maps, f"duplicate base map: {mid}")
        maps.add(mid)
        suffix = Path(entry["image"]).suffix
        require(suffix in (".png", ".webp"), f"unsupported base map format: {mid}")
        stem = f"{manifest['maps_root']}/{mid}/{entry['zoom']}/{mid}_{entry['zoom']}"
        expected_image = stem + suffix
        require(entry["image"] == expected_image, f"unexpected base map layout: {mid}")
        expected_mapping = stem + "_mapping.json"
        require(entry["mapping"] == expected_mapping, f"unexpected mapping layout: {mid}")
        size = image_size(resource(root, entry["image"]))
        require(size == (entry["width"], entry["height"]), f"base image size mismatch: {mid}")
        meta = json.loads(resource(root, entry["mapping"]).read_text(encoding="utf-8"))
        require(size == (meta["image_size"]["width"], meta["image_size"]["height"]),
                f"mapping image_size mismatch: {mid}")
        forward, inverse = matrix(meta["matrix"]), matrix(meta["inverse_matrix"])
        for a, b in ((forward, inverse), (inverse, forward)):
            for i in range(3):
                for j in range(3):
                    value = sum(a[i][k] * b[k][j] for k in range(3))
                    require(abs(value - int(i == j)) < 1e-7, f"matrices are not inverse: {mid}")
        referenced.update((entry["image"], entry["mapping"]))

    catalog = json.loads(resource(root, manifest["layer_catalog"]).read_text(encoding="utf-8"))
    require(catalog["schema_version"] == 1, "unsupported layer catalog version")
    ids = set()
    independent = 0
    for entry in catalog["layers"]:
        tier = entry["id"]
        require(tier not in ids, f"duplicate layer: {tier}")
        ids.add(tier)
        name = f"{manifest['layers_root']}/{entry['path']}"
        require(image_size(resource(root, name)) == (entry["width"], entry["height"]),
                f"layer image size mismatch: {tier}")
        bounds = entry["bounds"]
        values = [bounds[key] for key in ("west", "east", "south", "north")]
        require(all(type(v) in (int, float) and math.isfinite(v) for v in values),
                f"non-finite layer bounds: {tier}")
        require(values[0] < values[1] and values[2] < values[3], f"inverted bounds: {tier}")
        require(entry["map_category"] in ("layered", "independent"), f"unknown category: {tier}")
        independent += entry["map_category"] == "independent"
        referenced.add(name)
    coverage = manifest["coverage"]
    require(len(ids) == coverage["layer_count"], "layer count mismatch")
    require(independent == coverage["independent_layer_count"], "independent scene count mismatch")
    require(catalog.get("missing_logic_ids", []) == coverage["missing_logic_ids"],
            "missing layer declarations changed")
    require(not ids.intersection(coverage["missing_logic_ids"]), "missing layer also declared present")
    require(referenced == declared, f"manifest/catalog references differ: {referenced ^ declared}")
    return {"base_maps": len(maps), "layers": len(ids), "files": len(declared),
            "bytes": total, "missing_logic_ids": coverage["missing_logic_ids"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "localization")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.root), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        parser.exit(1, f"Invalid localization bundle: {exc}\n")


if __name__ == "__main__":
    main()
