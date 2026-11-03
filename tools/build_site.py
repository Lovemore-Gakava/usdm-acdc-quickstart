#!/usr/bin/env python3
"""
build_site.py — assemble the hosted application into _site/ from the pinned sources.

Nothing of CDISC's is committed to this repository. At build time this script fetches
cdisc-org/analysis-concepts at the commit pins.yml names, takes the application, its
libraries and models, and leaves out the sample datasets (ac-dc-app/data/sdtm and
ac-dc-app/data/adam, about 275 MB the browser never fetches). It adds one file from the
set-up repository at its tag, the M.MMRM implementation, and one script of this
repository's own, site/overlay.js, appended to the application's page.

    python tools/build_site.py            # writes _site/
    python tools/build_site.py --serve    # then serves it at http://localhost:8080/usdm-acdc-quickstart/

The serve option puts the site under the same path prefix GitHub Pages uses, because the
application computes its base path from the URL and a test at the root would not prove
the hosted case.

Python 3.9+, standard library and git only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
EXCLUDE = ("ac-dc-app/data/sdtm", "ac-dc-app/data/adam", "ac-dc-app/data/cdisc-library")
MMRM = "endpoints/04-vitals-cfb-mmrm/r_impl_mmrm.json"


def say(msg: str) -> None:
    print(msg, flush=True)


def read_pins() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (ROOT / "pins.yml").read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    for k in ("upstream", "upstream.commit", "factory", "factory.tag"):
        if not out.get(k):
            sys.exit(f"pins.yml names no {k}")
    return out


def check_readme(pins: dict[str, str]) -> None:
    """The README's version table and pins.yml must agree, or a reader is told one version
    and served another."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = [v for v in (pins["upstream.commit"][:7], pins["factory.tag"], pins.get("study.commit", "")) if v and v not in readme]
    if missing:
        sys.exit(f"README.md does not name the pinned version(s): {', '.join(missing)}")


def git(*args: str, cwd: Path | None = None, capture: bool = False) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=False)
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr.decode('utf-8', 'replace')}")
    return r.stdout.decode("utf-8", "replace") if capture else ""


def fetch_upstream(pins: dict[str, str], tmp: Path) -> Path:
    """A sparse, blob-less clone: only the paths the browser fetches are materialised."""
    up = tmp / "upstream"
    say(f"fetching {pins['upstream']} at {pins['upstream.commit'][:7]} (sparse) ...")
    git("clone", "--quiet", "--filter=blob:none", "--no-checkout", f"https://github.com/{pins['upstream']}.git", str(up))
    git("-c", "core.longpaths=true", "sparse-checkout", "set", "--no-cone", "/ac-dc-app/", "/lib/", "/model/", "/LICENSE",
        *[f"!/{e}/" for e in EXCLUDE], cwd=up)
    git("-c", "core.longpaths=true", "checkout", "--quiet", pins["upstream.commit"], cwd=up)
    for e in EXCLUDE:
        if (up / e).exists():
            sys.exit(f"sparse checkout did not exclude {e}")
    return up


def fetch_mmrm(pins: dict[str, str], tmp: Path) -> bytes:
    fac = tmp / "factory"
    say(f"fetching {pins['factory']} at {pins['factory.tag']} (one file) ...")
    git("clone", "--quiet", "--filter=blob:none", "--no-checkout", f"https://github.com/{pins['factory']}.git", str(fac))
    r = subprocess.run(["git", "show", f"{pins['factory.tag']}:{MMRM}"], cwd=fac, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"{MMRM} is not in the factory at {pins['factory.tag']}")
    return r.stdout


def assemble(pins: dict[str, str], up: Path, mmrm: bytes) -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    for d in ("ac-dc-app", "lib", "model"):
        shutil.copytree(up / d, SITE / d, ignore=shutil.ignore_patterns("serve.py", "__pycache__", ".DS_Store"))
    shutil.copy2(up / "LICENSE", SITE / "UPSTREAM-LICENSE")

    # The study list: the application loads every manifest entry at start-up. Only the file
    # the manifest names is kept; the other sample definitions in data/usdm are not fetched.
    usdm = SITE / "ac-dc-app" / "data" / "usdm"
    manifest = json.loads((usdm / "studies.json").read_text(encoding="utf-8"))
    entries = manifest if isinstance(manifest, list) else manifest["studies"]
    keep = {e["file"] for e in entries} | {"studies.json"}
    for f in usdm.iterdir():
        if f.name not in keep:
            f.unlink()

    overlay_dir = SITE / "ac-dc-app" / "data" / "overlay"
    overlay_dir.mkdir()
    (overlay_dir / "r_impl_mmrm.json").write_bytes(mmrm)

    # The overlay is appended to the application's page, the same way the set-up repository's
    # walkthrough server does it: the application's own files are not edited.
    index = SITE / "ac-dc-app" / "index.html"
    html = index.read_text(encoding="utf-8")
    tag = '<script src="../overlay.js"></script>'
    if "</body>" not in html:
        sys.exit("ac-dc-app/index.html has no </body> to append the overlay to")
    index.write_text(html.replace("</body>", tag + "\n</body>"), encoding="utf-8")

    shutil.copy2(ROOT / "site" / "overlay.js", SITE / "overlay.js")
    shutil.copy2(ROOT / "site" / "index.html", SITE / "index.html")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    (SITE / "versions.json").write_text(json.dumps({
        "upstream": pins["upstream"], "upstream_commit": pins["upstream.commit"],
        "factory": pins["factory"], "factory_tag": pins["factory.tag"],
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2) + "\n", encoding="utf-8")

    n = sum(1 for f in SITE.rglob("*") if f.is_file())
    mb = sum(f.stat().st_size for f in SITE.rglob("*") if f.is_file()) / 1e6
    say(f"_site/: {n} files, {mb:.1f} MB")


def serve(port: int) -> None:
    """Serve _site/ under /usdm-acdc-quickstart/, as GitHub Pages will."""
    import functools
    import http.server
    tmp = Path(tempfile.mkdtemp(prefix="quickstart-serve-"))
    shutil.copytree(SITE, tmp / "usdm-acdc-quickstart")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp))
    http.server.SimpleHTTPRequestHandler.extensions_map.update({".js": "application/javascript", ".mjs": "application/javascript", ".json": "application/json"})
    httpd = http.server.ThreadingHTTPServer(("", port), handler)
    say(f"serving http://localhost:{port}/usdm-acdc-quickstart/  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serve", action="store_true", help="serve _site/ under the Pages path prefix after building")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-build", action="store_true", help="with --serve: serve the existing _site/")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    pins = read_pins()
    if not args.no_build:
        check_readme(pins)
        with tempfile.TemporaryDirectory(prefix="quickstart-build-") as t:
            tmp = Path(t)
            up = fetch_upstream(pins, tmp)
            mmrm = fetch_mmrm(pins, tmp)
            assemble(pins, up, mmrm)
    if args.serve:
        serve(args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
