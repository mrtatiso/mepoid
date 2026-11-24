#!/usr/bin/env python3
"""fetch: puts the pieces mepoid uses next to mepoid.py, checked by sha256.

    $ python3 fetch.py

Downloads band80.py, vox.py, onyon.py, alix.py and clean.tecy from their
repositories into this folder. Each file is checked against the sha256 below
before it is written: a file that does not match is not saved, and nothing
already here is changed. Files already here with the right sha256 are kept.

These are the exact versions mepoid v1 was built and tested with. A new version
of any piece means a new list here.
"""
import hashlib
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = "https://raw.githubusercontent.com/mrtatiso/{repo}/main/{name}"

PIECES = [
    ("band80", "band80.py", "00559e6cd83de05841f1cf7be441604a4ef37460518ce5665e34c150aa8377ca"),
    ("vox", "vox.py", "30969691d2a35e203662336681476120edc8524a4d7f9e7e0fa46beab398d128"),
    ("onyon", "onyon.py", "1bfd794c53085815d0b01f46bab0fae4f4716c3d23fac753bc34445f19acbbf9"),
    ("alix", "alix.py", "bd9eb93a883ae7960d6eab61b5a3b4fa5eb2bb9a6ef34723b81958920dc2b513"),
    ("alix", "clean.tecy", "a2593fa55ce78bdea018fdf3b261d44b8131f35eda059bf063db3ab087ad2341"),
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(folder: str = HERE, get=None) -> bool:
    """Every piece in folder, checked. Returns True if all are there and right."""
    get = get or (lambda url: urllib.request.urlopen(url, timeout=30).read())
    ok = True
    for repo, name, digest in PIECES:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                if _sha(f.read()) == digest:
                    print(f"  ok        {name}")
                    continue
        url = RAW.format(repo=repo, name=name)
        try:
            data = get(url)
        except OSError as e:
            print(f"  failed    {name}: {e}", file=sys.stderr)
            ok = False
            continue
        if _sha(data) != digest:
            print(f"  refused   {name}: sha256 differs from the expected version", file=sys.stderr)
            ok = False
            continue
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        print(f"  fetched   {name}")
    return ok


def main() -> int:
    if fetch():
        print("all pieces in place")
        return 0
    print("some pieces are missing: mepoid will not run until they are here", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
