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

Friends (v1.1): one FRIVOX line per friend, each with its own salt.

    FRIVOX=<salt>:<their pubvox, sealed>

    mine     X25519(shake_256("frivox1|" + vox(salt, key)), 9)   what you give them
    theirs   S − t·B, t = shake_256("frisel1|" + vox(salt, key))  what they gave you
    frivox   shake_256("frivox1-pair|" + X25519(mine, theirs) + both pubvoxes, sorted)

The pubvox they gave you is sealed as a point (S = P + t·B on ed25519), never
by adding digits: any key opens every FRIVOX into a valid key of the prime-order
subgroup, so nothing in the file tells the right key apart. The frivox is the
seed for the client (cypo), which runs the ratchet. Older .mepo files without
FRIVOX lines open exactly as before.

SUBS come later, when the piece that uses them exists.
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

__version__ = "1.1.0"
__all__ = ["create", "open_", "pubvox", "friend_new", "friend_set"]

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


# ---------- friends: FRIVOX (v1.1) ----------
# Their pubvox is sealed as an ed25519 point: S = P + t·B. Adding a multiple of
# B keeps it in the prime-order subgroup, so any key opens it into a valid
# pubvox. Sealing by digits would not: about half of all 32-byte values are on
# the twist, and with several friends the right key would be the only one that
# gives every pubvox on the curve. The ed25519 math is onyon's (pinned by sha256).

def _digits(band: str) -> bytes:
    d = "".join(c for c in band if c in "0123456789")
    if len(d) != 80:
        raise ValueError("a syvox must have 80 digits")
    return d.encode()


def _mine(s: str) -> bytes:
    """Your private half for this friendship, from vox(salt, key)."""
    return hashlib.shake_256(b"frivox1|" + _digits(s)).digest(32)


def _t(s: str) -> int:
    return int.from_bytes(hashlib.shake_256(b"frisel1|" + _digits(s)).digest(64), "little") % onyon.L


def _to_point(pub: str):
    """The ed25519 point of a pubvox (Montgomery u, 32 bytes hex). ValueError if it
    is not a key of the prime-order subgroup."""
    try:
        raw = bytes.fromhex(pub.strip())
    except ValueError:
        raise ValueError("a pubvox is 64 hex characters") from None
    if len(raw) != 32:
        raise ValueError("a pubvox is 64 hex characters")
    u = int.from_bytes(raw, "little")
    if u >= _P or (u + 1) % _P == 0:
        raise ValueError("not a valid pubvox")
    y = (u - 1) * pow(u + 1, _P - 2, _P) % _P
    pt = onyon._decode(y.to_bytes(32, "little"))
    if pt is None or onyon._is_zero(pt) or not onyon._is_zero(onyon._mul(onyon.L, pt)):
        raise ValueError("not a valid pubvox")
    return pt


def _to_pub(pt) -> str:
    y = int.from_bytes(onyon._encode(pt), "little") & ((1 << 255) - 1)
    return ((1 + y) * pow(1 - y, _P - 2, _P) % _P).to_bytes(32, "little").hex()


def _seal_pub(s: str, pub: str) -> str:
    return onyon._encode(onyon._add(_to_point(pub), onyon._mul(_t(s), onyon.B))).hex()


def _open_pub(s: str, sealed: str) -> str:
    raw = bytes.fromhex(sealed)
    pt = onyon._decode(raw) if len(raw) == 32 else None
    if pt is None:
        raise ValueError("a sealed pubvox is not a point")
    return _to_pub(onyon._add(pt, onyon._neg(onyon._mul(_t(s), onyon.B))))


def _frivox(mine: bytes, mine_pub: str, theirs: str) -> str:
    shared = _x25519(mine, int.from_bytes(bytes.fromhex(theirs), "little")).to_bytes(32, "little")
    a, b = sorted((bytes.fromhex(mine_pub), bytes.fromhex(theirs)))
    return hashlib.shake_256(b"frivox1-pair|" + shared + a + b).hexdigest(32)


def _friend(salt: str, sealed: str, key: str) -> dict:
    s = vox.vox(salt, key)
    k = _mine(s)
    mine = _x25519(k, 9).to_bytes(32, "little").hex()
    if not sealed:
        return {"MINE": mine, "THEIRS": None, "FRIVOX": None}
    theirs = _open_pub(s, sealed)
    return {"MINE": mine, "THEIRS": theirs, "FRIVOX": _frivox(k, mine, theirs)}


# ---------- file ----------

def _read(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    if not lines or lines[0] != HEADER:
        raise ValueError(f"{path}: not a {HEADER} file")
    fields = {"FRIVOX": []}
    for l in lines[1:]:
        name, _, value = l.partition("=")
        if name == "FRIVOX":                    # one line per friend, in order
            fields["FRIVOX"].append(value)
        else:
            fields[name] = value
    missing = [f for f in FIELDS if f not in fields]
    if missing:
        raise ValueError(f"{path}: missing {', '.join(missing)}")
    return fields


def _write(path: str, f: dict) -> None:
    """Rewrite the same .mepo atomically: the old one stays whole until the new one is in."""
    tmp = path + ".tmp"
    with open(tmp, "x", encoding="utf-8") as out:
        out.write(f"{HEADER}\n" + "".join(f"{k}={f[k]}\n" for k in FIELDS)
                  + "".join(f"FRIVOX={v}\n" for v in f["FRIVOX"]))
    os.replace(tmp, path)


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
        "FRIVOXS": [_friend(*v.split(":"), key) for v in f["FRIVOX"]],
    }


def friend_new(path: str, key: str) -> tuple:
    """A new friend slot. Returns (its number, your pubvox for that friend)."""
    f = _read(path)
    salt = band80.gen(4, 20)
    f["FRIVOX"].append(f"{salt}:")
    _write(path, f)
    return len(f["FRIVOX"]), _friend(salt, "", key)["MINE"]


def friend_set(path: str, n: int, theirs: str, key: str) -> str:
    """Seal the pubvox friend n gave you into slot n. Returns the frivox."""
    f = _read(path)
    if not 1 <= n <= len(f["FRIVOX"]):
        raise ValueError(f"there is no friend {n}")
    _to_point(theirs)
    salt = f["FRIVOX"][n - 1].split(":")[0]
    f["FRIVOX"][n - 1] = f"{salt}:{_seal_pub(vox.vox(salt, key), theirs)}"
    _write(path, f)
    return _friend(*f["FRIVOX"][n - 1].split(":"), key)["FRIVOX"]


# ---------- terminal ----------

USAGE = """usage:
  mepoid create <alias> <birthnest.onion>    a new .mepo here (key is asked twice)
  mepoid open <file.mepo>                    the profile (key is asked)
  mepoid friend new <file.mepo>              a friend slot and your pubvox for them
  mepoid friend set <file.mepo> <n> <pubvox> seal the pubvox friend n gave you"""


def _key(twice=False) -> str:
    if not sys.stdin.isatty():
        return sys.stdin.readline().rstrip("\n")
    k = getpass.getpass("key: ")
    if twice and getpass.getpass("key again: ") != k:
        raise ValueError("the two keys differ: nothing was written")
    return k


def _confirm(path: str, key: str) -> None:
    """The key is never checked, so you check it: a typo here would seal a friend
    under someone else's profile without saying so."""
    a_salt, a_sealed = _read(path)["ALIX"].split(":")
    alias = alix.open_(vox.vox(a_salt, key), a_sealed)
    print(f"ALIX       {alias}    is this your profile? [y/N] ", end="", file=sys.stderr, flush=True)
    if sys.stdin.readline().strip().lower() not in ("y", "yes", "s", "si", "sí"):
        raise ValueError("not confirmed: nothing was written")


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
                if name != "FRIVOXS":
                    print(f"{name:<10} {value}")
            for i, fr in enumerate(value, 1):
                print(f"FRIVOX {i:<3} mine   {fr['MINE']}")
                print(f"           theirs {fr['THEIRS'] or '— waiting: mepoid friend set'}")
                print(f"           frivox {fr['FRIVOX'] or '—'}")
        elif len(args) == 3 and args[:2] == ["friend", "new"]:
            key = _key()
            _confirm(args[2], key)
            n, mine = friend_new(args[2], key)
            print(f"FRIVOX {n}   give them: {mine}")
        elif len(args) == 5 and args[:2] == ["friend", "set"] and args[3].isdigit():
            _to_point(args[4])
            key = _key()
            _confirm(args[2], key)
            print(f"FRIVOX {args[3]}   frivox: {friend_set(args[2], int(args[3]), args[4], key)}")
        else:
            print(USAGE, file=sys.stderr)
            return 2
    except (OSError, ValueError) as e:
        print(f"mepoid: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
