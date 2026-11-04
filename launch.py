#!/usr/bin/env python3
"""
launch.py - from nothing to the running application, in one command.

    python launch.py              # python3 on macOS and Linux; py -3 on Windows
    python launch.py --check      # report what the machine has and lacks; change nothing
    python launch.py --no-browser # start the server without opening a browser tab

It does what the README's set-up describes, in order, and stops at the first thing it
cannot do, saying what and why:

  1. git, and a Python 3.10 or newer, are on this machine
  2. the set-up repository is cloned beside this file at TAG, with CDISC's application
     as its submodule; on Windows the clone is made with long paths enabled, so it does
     not stop part-way on CDISC's long file names, and nothing global is changed
  3. no earlier run is in the way: nothing already listening on the port, and nothing a
     server that was not stopped with Ctrl-C left staged in the submodule
  4. its tools/bootstrap.py has run: the Python environment, the study at its pin, a check
  5. Windows only: the submodule's line endings are as the engine expects
  6. tools/walkthrough.py serve is running, and the browser is open on the application

Safe to re-run: every step reports when it was already done. Ctrl-C stops the server, which
cleans up after itself. TAG below, the README's version table and pins.yml must name the
same tag; tools/build_site.py refuses to build when they disagree.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

REPO_URL = "https://github.com/Lovemore-Gakava/usdm-acdc-in-practice.git"
TAG = "quickstart-2026-11.2"
HERE = Path(__file__).resolve().parent
DEST = HERE / "usdm-acdc-in-practice"
SUB = DEST / "upstream" / "analysis-concepts"
PORT = 8080
APP_URL = f"http://localhost:{PORT}/ac-dc-app/index.html"
GUIDE_URL = f"http://localhost:{PORT}/walkthrough"
WINDOWS = os.name == "nt"
# `git -c` is passed to the child git processes too, so the submodule clone sees it.
LONGPATHS = ["-c", "core.longpaths=true"] if WINDOWS else []

FAIL: list[str] = []


def say(msg: str) -> None:
    print(msg, flush=True)


def step(n: str, msg: str) -> None:
    print(f"\n[{n}] {msg}", flush=True)


def run(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, check=check,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def git(*args: str, cwd: Path | None = None) -> str:
    return run("git", *args, cwd=cwd, check=False).stdout.strip()


def version_of(exe: str) -> tuple[int, int] | None:
    try:
        v = subprocess.run([exe, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, check=True, timeout=30).stdout.strip()
        major, minor = v.split(".")
        return int(major), int(minor)
    except Exception:
        return None


def newest_python() -> tuple[str, tuple[int, int]] | None:
    """A Python 3.10 or newer, as tools/bootstrap.py looks for one: this interpreter first."""
    cands = [sys.executable] + [f"python3.{m}" for m in range(14, 9, -1)] + ["python3", "python"]
    for c in cands:
        exe = c if Path(c).is_absolute() else shutil.which(c)
        if not exe:
            continue
        v = version_of(exe)
        if v and v >= (3, 10):
            return exe, v
    return None


def venv_python() -> Path:
    return DEST / ".venv" / ("Scripts" if WINDOWS else "bin") / ("python.exe" if WINDOWS else "python")


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


# --------------------------------------------------------------------------- steps

def do_requirements() -> None:
    step("1/6", "git and Python")
    g = shutil.which("git")
    if not g:
        say("  MISSING - git. Install it from https://git-scm.com and re-run.")
        FAIL.append("git")
    else:
        say(f"  ok - {git('--version')}")
    py = newest_python()
    if not py:
        say("  MISSING - no Python 3.10 or newer found. Install one from https://python.org and re-run.")
        say(f"  (this script is running on {sys.version.split()[0]}; the set-up needs 3.10+ for its dependencies)")
        FAIL.append("python")
    else:
        say(f"  ok - Python {py[1][0]}.{py[1][1]} at {py[0]}")


def do_clone(check_only: bool) -> None:
    step("2/6", f"the set-up repository at {TAG}, with CDISC's application inside it")
    if FAIL:
        say("  skipped - fix the step above first")
        return
    if not (DEST / ".git").exists():
        if check_only:
            say(f"  MISSING - nothing at {DEST}")
            FAIL.append("clone")
            return
        say(f"  cloning into {DEST} - about 80 MB, a minute or two ...")
        p = run("git", *LONGPATHS, "clone", "--quiet", "--recurse-submodules", "--branch", TAG, REPO_URL, str(DEST), check=False)
        if p.returncode != 0:
            say("  FAILED:\n    " + p.stderr.strip().replace("\n", "\n    "))
            FAIL.append("clone")
            return
    want = git("rev-parse", f"{TAG}^{{commit}}", cwd=DEST)
    if not want:
        if check_only:
            say(f"  the clone does not know the tag {TAG}")
            FAIL.append("clone")
            return
        run("git", "fetch", "--quiet", "--tags", "origin", cwd=DEST, check=False)
        want = git("rev-parse", f"{TAG}^{{commit}}", cwd=DEST)
    head = git("rev-parse", "HEAD", cwd=DEST)
    if head != want:
        if check_only:
            say(f"  at {head[:7]}, not the tag {TAG} ({want[:7]})")
            FAIL.append("clone")
            return
        p = run("git", "checkout", "--quiet", TAG, cwd=DEST, check=False)
        if p.returncode != 0:
            say("  FAILED to check out the tag:\n    " + p.stderr.strip().replace("\n", "\n    "))
            FAIL.append("clone")
            return
    if not (SUB / "lib").is_dir() and not check_only:
        run("git", *LONGPATHS, "submodule", "update", "--init", "--quiet", cwd=DEST, check=False)
    if WINDOWS and not check_only:
        # Later checkouts inside the clone, by bootstrap.py or by hand, need the same setting;
        # local to these two repositories, so nothing on the machine changes.
        for repo in (DEST, SUB):
            if (repo / ".git").exists() and git("config", "--get", "core.longpaths", cwd=repo) != "true":
                run("git", "config", "core.longpaths", "true", cwd=repo, check=False)
    if (SUB / "lib").is_dir():
        say(f"  ok - {DEST.name} at {TAG} ({want[:7]}), submodule at {git('rev-parse', '--short', 'HEAD', cwd=SUB)}")
    else:
        say("  MISSING - the submodule did not check out; see the git output above")
        FAIL.append("clone")


def do_leftovers(check_only: bool) -> None:
    step("3/6", "nothing from an earlier run in the way")
    if FAIL:
        say("  skipped - fix the steps above first")
        return
    if port_open(PORT):
        say(f"  something is already listening on port {PORT}.")
        say(f"  If it is an earlier run of this, the application is at {APP_URL}; otherwise stop it and re-run.")
        FAIL.append("port")
        return
    dirt = git("status", "--short", cwd=SUB)
    if not dirt:
        say("  ok - the submodule is clean")
        return
    if not venv_python().is_file():
        say("  the submodule is not clean; the bootstrap, next, will say what it can do about it")
        return
    # A server stopped without Ctrl-C leaves what it staged. Its own `clean` removes exactly
    # that and nothing else, and says so if anything foreign remains for the bootstrap to judge.
    if check_only:
        say("  the submodule carries files a server left staged; run without --check to clean them:")
        for line in dirt.splitlines()[:6]:
            say("    " + line)
        FAIL.append("leftovers")
        return
    say("  a server left files staged in the submodule; cleaning them with tools/walkthrough.py clean")
    p = run(str(venv_python()), str(DEST / "tools" / "walkthrough.py"), "clean", cwd=DEST, check=False)
    for line in (p.stdout + p.stderr).splitlines():
        say("    " + line)


def do_bootstrap(check_only: bool) -> None:
    step("4/6", "tools/bootstrap.py - the Python environment, the study at its pin, and a check")
    if FAIL:
        say("  skipped - fix the steps above first")
        return
    cmd = [sys.executable, str(DEST / "tools" / "bootstrap.py")] + (["--check"] if check_only else [])
    say("  running it; its own report follows, indented\n")
    p = subprocess.run(cmd, cwd=str(DEST), capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in (p.stdout + p.stderr).splitlines():
        say("    " + line)
    say("")
    if p.returncode != 0:
        say("  the bootstrap did not finish; what it said is above")
        FAIL.append("bootstrap")
    elif not venv_python().is_file():
        say(f"  MISSING - no interpreter at {venv_python()}")
        FAIL.append("bootstrap")
    else:
        say("  ok")


def do_line_endings(check_only: bool) -> None:
    step("5/6", "Windows line endings in the submodule")
    if not WINDOWS:
        say("  not needed on this platform")
        return
    if FAIL or not (SUB / ".git").exists():
        say("  skipped - fix the steps above first")
        return
    if git("config", "--get", "core.autocrlf", cwd=SUB) == "false":
        say("  ok - core.autocrlf is false in the submodule")
        return
    if check_only:
        say("  not set - the engine refuses to parse at step 8 until it is")
        FAIL.append("line-endings")
        return
    run("git", "config", "core.autocrlf", "false", cwd=SUB, check=False)
    p = run("git", "checkout", "--", ".", cwd=SUB, check=False)
    if p.returncode != 0:
        say("  FAILED:\n    " + p.stderr.strip().replace("\n", "\n    "))
        FAIL.append("line-endings")
        return
    say("  set core.autocrlf=false in the submodule and re-checked out its files")


def do_serve(open_browser: bool) -> int:
    step("6/6", "tools/walkthrough.py serve")
    if port_open(PORT):
        say(f"  something is already listening on port {PORT}.")
        say(f"  If it is an earlier run of this, the application is at {APP_URL}; otherwise stop it and re-run.")
        return 1
    say("  starting the server; it stages the study first, about a minute. Its output follows.")
    say(f"  The application will open at {APP_URL}")
    say(f"  The click-by-click guide is at {GUIDE_URL}")
    say("  Ctrl-C stops it, and it cleans up after itself.\n")
    proc = subprocess.Popen([str(venv_python()), str(DEST / "tools" / "walkthrough.py"), "serve"], cwd=str(DEST))
    try:
        deadline = time.time() + 300
        while time.time() < deadline:
            if proc.poll() is not None:
                say(f"\n  the server stopped before it was up (exit {proc.returncode}); what it said is above")
                return 1
            if port_open(PORT):
                break
            time.sleep(1)
        else:
            say("\n  the server did not answer within five minutes; what it said is above")
            return 1
        if open_browser:
            webbrowser.open(APP_URL)
        return proc.wait()
    except KeyboardInterrupt:
        # The same Ctrl-C reaches the server; let it finish removing what it staged.
        try:
            proc.wait(timeout=60)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            proc.terminate()
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Set up and start the application from nothing.")
    ap.add_argument("--check", action="store_true", help="report what the machine has and lacks; change nothing")
    ap.add_argument("--no-browser", action="store_true", help="start the server without opening a browser tab")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    if sys.version_info < (3, 9):
        say(f"this script needs Python 3.9 or newer to run; this is {sys.version.split()[0]}")
        return 1

    say(f"launch - {HERE}")
    if args.check:
        say("(--check: reporting only, nothing will be changed)")
    do_requirements()
    do_clone(args.check)
    do_leftovers(args.check)
    do_bootstrap(args.check)
    do_line_endings(args.check)
    if FAIL:
        say(f"\nnot ready: {', '.join(FAIL)}. Fix what is marked above and re-run; what was done is kept.")
        return 1
    if args.check:
        say(f"\nready. Run without --check to start the server; the application is then at {APP_URL}")
        return 0
    return do_serve(not args.no_browser)


if __name__ == "__main__":
    sys.exit(main())
