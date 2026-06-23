#!/usr/bin/env python3
"""Generate a curated CycloneDX SBOM for a published linux-utils-oci image.

Reads from the environment (set by the SBOM workflow step, resolved from the
build-stage image):
  COMPONENT               squashfs-tools | mkfs
  SQUASHFS_TOOLS_COMMIT   resolved commit of plougher/squashfs-tools
  SQUASHFS_TOOLS_VERSION  git-describe of same
  ZLIB_NG_COMMIT          resolved commit of zlib-ng/zlib-ng
  ZLIB_NG_VERSION         git-describe of same
  E2FSPROGS_COMMIT        resolved commit of e2fsprogs
  E2FSPROGS_VERSION       git-describe of same (the build-discovered release tag)

Writes <COMPONENT>.cdx.json (CycloneDX 1.6) in the current directory.
"""
import json
import os
import sys


def github_source(name, gh_path, commit, version, ctype="application"):
    """A GitHub-hosted source component, pinned to commit in its purl."""
    purl = "pkg:github/%s" % gh_path
    if commit:
        purl = "%s@%s" % (purl, commit)
    component = {
        "bom-ref": purl,
        "type": ctype,
        "name": name,
        "purl": purl,
        "externalReferences": [
            {"type": "vcs", "url": "https://github.com/%s.git" % gh_path}
        ],
    }
    if version:
        component["version"] = version
    return component


def e2fsprogs_source(commit, version):
    """e2fsprogs lives on git.kernel.org (not GitHub), so it is a pkg:generic
    component with the commit carried as a property (purls for generic sources
    have no standard commit qualifier)."""
    purl = "pkg:generic/e2fsprogs"
    if version:
        purl = "%s@%s" % (purl, version)
    component = {
        "bom-ref": purl,
        "type": "application",
        "name": "e2fsprogs",
        "purl": purl,
        "externalReferences": [
            {
                "type": "vcs",
                "url": "https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git",
            }
        ],
    }
    if version:
        component["version"] = version
    if commit:
        component["properties"] = [
            {"name": "dev.edera.source.commit", "value": commit}
        ]
    return component


def build_sources(comp):
    if comp == "squashfs-tools":
        return [
            github_source(
                "squashfs-tools",
                "plougher/squashfs-tools",
                os.environ.get("SQUASHFS_TOOLS_COMMIT", ""),
                os.environ.get("SQUASHFS_TOOLS_VERSION", ""),
            ),
            # zlib-ng is built static (zlib-compat) and linked into the binaries.
            github_source(
                "zlib-ng",
                "zlib-ng/zlib-ng",
                os.environ.get("ZLIB_NG_COMMIT", ""),
                os.environ.get("ZLIB_NG_VERSION", ""),
                ctype="library",
            ),
        ]
    if comp == "mkfs":
        return [
            e2fsprogs_source(
                os.environ.get("E2FSPROGS_COMMIT", ""),
                os.environ.get("E2FSPROGS_VERSION", ""),
            )
        ]
    print("ERROR: unknown COMPONENT %r" % comp, file=sys.stderr)
    sys.exit(1)


def main():
    comp = os.environ["COMPONENT"]
    sources = build_sources(comp)

    image_ref = "%s@nightly" % comp
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {
                "bom-ref": image_ref,
                "type": "container",
                "name": comp,
            }
        },
        "components": sources,
        "dependencies": [
            {
                "ref": image_ref,
                "dependsOn": [c["bom-ref"] for c in sources if c.get("bom-ref")],
            }
        ],
    }

    with open("%s.cdx.json" % comp, "w") as out:
        json.dump(document, out, indent=2)
        out.write("\n")

    print(
        json.dumps(
            {"component": comp, "components": len(sources)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
