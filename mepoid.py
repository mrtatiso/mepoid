#!/usr/bin/env python3
"""mepoid: builds and opens a .mepo, the profile that opens with any key.

    $ mepoid create maria <birthnest.onion>     key: · key again:  → tawos.mepo
    $ mepoid open tawos.mepo                    key:               → the profile

The file is named after the alias anyone sees, and holds only band80s and a
sealed onion:

    mepoid/1
    ALIX=<salt>:<sealed alias>
    BIRTHNEST=<salt>:<sealed onion>
    SYVOX=<salt>
    PRIVOX=<salt>

Every field has its own salt, made by band80. Opening runs vox once per field
with that salt and the key, and gives each result to the piece that knows the
field. The key goes only to vox; nothing else sees it.

    ALIX       alix.open_(vox(salt, key), sealed)     the alias
    BIRTHNEST  onyon.open_(vox(salt, key), sealed)    the onion
    SYVOX      vox(salt, key)                         your syvox
    PRIVOX     vox(salt, key)                         your private voice
    PUBVOX     X25519(privox)                         your public voice

PUBVOX is never written: it comes from PRIVOX each time. Written in clear, it
would let anyone try keys until one gave the same PUBVOX.

Any key opens the file into a full profile: another alias, another valid
onion, another syvox, privox and pubvox. Only the right key gives yours.
Nothing in the file says which one is right.

band80.py, vox.py, onyon.py, alix.py and clean.tecy must sit next to
mepoid.py: fetch.py downloads them and checks their sha256, and mepoid checks
them again every time it starts.

FRIVOXS and SUBS come later, when the pieces that use them exist.
"""
import getpass
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetch import PIECES  # noqa: E402

for _repo, _name, _digest in PIECES:      # the pieces next to mepoid.py, exactly as tested
    _path = os.path.join(HERE, _name)
    if not os.path.exists(_path):
        raise SystemExit(f"mepoid: {_name} is missing: run python3 fetch.py")
    with open(_path, "rb") as _f:
        if hashlib.sha256(_f.read()).hexdigest() != _digest:
            raise SystemExit(f"mepoid: {_name} is not the expected version: run python3 fetch.py")

import alix  # noqa: E402
import band80  # noqa: E402
import onyon  # noqa: E402
import vox  # noqa: E402

__version__ = "1.0.0"
__all__ = ["create", "open_", "pubvox"]

HEADER = "mepoid/1"
FIELDS = ("ALIX", "BIRTHNEST", "SYVOX", "PRIVOX")


# ---------- voices: X25519 (RFC 7748) ----------
# Here until the voices have their own library (with FRIVOXS and the ratchet).

_P = 2 ** 255 - 19


def _x25519(k: bytes, u: int) -> int:
    k = bytearray(k)
    k[0] &= 248
    k[31] = (k[31] & 127) | 64
    n = int.from_bytes(k, "little")
    x1, x2, z2, x3, z3, swap = u, 1, 0, u, 1, 0
    for t in reversed(range(255)):
        bit = (n >> t) & 1
        if swap ^ bit:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a, b, c, d = x2 + z2, x2 - z2, x3 + z3, x3 - z3
        aa, bb, da, cb = a * a, b * b, d * a, c * b
        e = aa - bb
        x3, z3 = (da + cb) ** 2 % _P, x1 * (da - cb) ** 2 % _P
        x2, z2 = aa * bb % _P, e * (aa + 121665 * e) % _P
    if swap:
        x2, z2 = x3, z3
    return x2 * pow(z2, _P - 2, _P) % _P


def pubvox(privox: str) -> str:
    """The public voice (32 bytes, hex) of a privox (80 digits)."""
    digits = "".join(c for c in privox if c in "0123456789")
    if len(digits) != 80:
        raise ValueError("a privox must have 80 digits")
    k = hashlib.shake_256(b"privox1|" + digits.encode()).digest(32)
    return _x25519(k, 9).to_bytes(32, "little").hex()


# ---------- file ----------

def _read(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines or lines[0] != HEADER:
        raise ValueError(f"{path}: not a {HEADER} file")
    fields = {}
    for l in lines[1:]:
        name, _, value = l.partition("=")
        fields[name] = value
    missing = [f for f in FIELDS if f not in fields]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)}")
    return fields


def create(folder: str, alias: str, birthnest: str, key: str) -> str:
    """Build a new .mepo in folder and return its path. Never writes over a file."""
    if not alix.check(alias):
        raise ValueError(f"'{alias}' cannot be an alias: check it with alix check")
    onyon.parse(birthnest)
    salts = {f: band80.gen(4, 20) for f in FIELDS}
    open_alias = vox.vox(salts["ALIX"], key)
    sealed_onion = onyon.seal(vox.vox(salts["BIRTHNEST"], key), birthnest)
    for _ in range(100):                       # another sealing, another public name
        sealed_alias = alix.seal(open_alias, alias)
        path = os.path.join(folder, alix.show(sealed_alias) + ".mepo")
        try:
            with open(path, "x", encoding="utf-8") as f:
                f.write(f"{HEADER}\n"
                        f"ALIX={salts['ALIX']}:{sealed_alias}\n"
                        f"BIRTHNEST={salts['BIRTHNEST']}:{sealed_onion}\n"
                        f"SYVOX={salts['SYVOX']}\n"
                        f"PRIVOX={salts['PRIVOX']}\n")
            return path
        except FileExistsError:
            continue
    raise ValueError("could not find a free name for the .mepo")


def open_(path: str, key: str) -> dict:
    """The profile in a .mepo, opened with this key. Any key works."""
    f = _read(path)
    a_salt, a_sealed = f["ALIX"].split(":")
    b_salt, b_sealed = f["BIRTHNEST"].split(":")
    privox = vox.vox(f["PRIVOX"], key)
    return {
        "ALIX": alix.open_(vox.vox(a_salt, key), a_sealed),
        "BIRTHNEST": onyon.open_(vox.vox(b_salt, key), b_sealed),
        "SYVOX": vox.vox(f["SYVOX"], key),
        "PRIVOX": privox,
        "PUBVOX": pubvox(privox),
    }


# ---------- terminal ----------

USAGE = """usage:
  mepoid create <alias> <birthnest.onion>    a new .mepo here (key is asked twice)
  mepoid open <file.mepo>                    the profile (key is asked)"""


def _key(twice=False) -> str:
    if not sys.stdin.isatty():
        return sys.stdin.readline().rstrip("\n")
    k = getpass.getpass("key: ")
    if twice and getpass.getpass("key again: ") != k:
        raise ValueError("the two keys differ: nothing was written")
    return k


def main(args=None) -> int:
    args = sys.argv[1:] if args is None else args
    try:
        if len(args) == 3 and args[0] == "create":
            if not alix.check(args[1]):
                raise ValueError(f"'{args[1]}' cannot be an alias: check it with alix check")
            onyon.parse(args[2])
            print(os.path.basename(create(".", args[1], args[2], _key(twice=True))))
        elif len(args) == 2 and args[0] == "open":
            for name, value in open_(args[1], _key()).items():
                print(f"{name:<10} {value}")
        else:
            print(USAGE, file=sys.stderr)
            return 2
    except (OSError, ValueError) as e:
        print(f"mepoid: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
