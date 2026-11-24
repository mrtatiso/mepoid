# mepoid

Builds and opens a `.mepo`: the profile that opens with any key, and only shows yours with your key.

```
$ python3 mepoid.py create maria duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion
key:
key again:
preparka.mepo

$ python3 mepoid.py open preparka.mepo
key:                                    holamundo
ALIX       maria
BIRTHNEST  duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion
SYVOX      66691774805121606906.27468121245176695930.85223805807896443272.49276755105776295566
PRIVOX     27558634573436314820.81948528818950063564.17815129468628825157.72267026485055839767
PUBVOX     b647575bc89f37b83764cde5c35cb61bb48f291a668b7736557e1e845db1a831

$ python3 mepoid.py open preparka.mepo
key:                                    pedro
ALIX       rodcios
BIRTHNEST  f4ng6fj4zhzaj4lkd4o7evqrruf6pqwhesgwa7n5ils3vwaxnazl6xyd.onion
SYVOX      15082258765652185409.53637343250431172006.69047664085854618218.94448559311863731221
PRIVOX     06576489174115912661.41985263727627678163.21443894050521580105.13968723900381214582
PUBVOX     7fd6e9490238babfac623ce9de9580e80f08e1a23e55eb465bb5e0a10cb89221
```

PUBVOX is shown so you can check it, not to hand out: each friend gets their own (see Friends).

mepoid only coordinates. The key goes to [vox](https://github.com/mrtatiso/vox) and nowhere else; each field is sealed and opened by its own piece.

## Install

Everything lives in one folder: mepoid.py and the pieces it uses, next to each other.

```
git clone https://github.com/mrtatiso/mepoid
cd mepoid
python3 fetch.py
```

`fetch.py` downloads [band80](https://github.com/mrtatiso/band80), [vox](https://github.com/mrtatiso/vox), [onyon](https://github.com/mrtatiso/onyon), [alix](https://github.com/mrtatiso/alix) and alix's `clean.tecy` into the folder. Each file is checked against its sha256 before it is saved: one that does not match is refused, and nothing already there is changed. mepoid checks them again every time it starts, and stops if one is missing or different.

| file | from | sha256 |
|---|---|---|
| band80.py | band80 | `00559e6cd83de05841f1cf7be441604a4ef37460518ce5665e34c150aa8377ca` |
| vox.py | vox | `30969691d2a35e203662336681476120edc8524a4d7f9e7e0fa46beab398d128` |
| onyon.py | onyon | `1bfd794c53085815d0b01f46bab0fae4f4716c3d23fac753bc34445f19acbbf9` |
| alix.py | alix | `bd9eb93a883ae7960d6eab61b5a3b4fa5eb2bb9a6ef34723b81958920dc2b513` |
| clean.tecy | alix | `a2593fa55ce78bdea018fdf3b261d44b8131f35eda059bf063db3ab087ad2341` |

The fetched files are in `.gitignore`: this repository holds only mepoid, and each piece stays in its own.

```
python3 mepoid.py create <alias> <birthnest.onion>
python3 mepoid.py open <file.mepo>
python3 mepoid.py friend new <file.mepo>
python3 mepoid.py friend set <file.mepo> <n> <their pubvox>
```

The key is asked without showing it, twice when creating. From a script it can come through stdin, and for `friend` the confirmation comes on the next line.

### Python

```python
import mepoid

path = mepoid.create(".", "maria", birthnest, key)    # → "./preparka.mepo"
profile = mepoid.open_(path, key)                       # → dict, in memory only
n, mine = mepoid.friend_new(path, key)                  # → slot number, your pubvox for them
frivox = mepoid.friend_set(path, n, theirs, key)        # → the seed for the client
```

## The .mepo

Named after the alias anyone sees, so the name says nothing either. Inside, only band80s and a sealed onion:

```
mepoid/1
ALIX=<salt>:<sealed alias>
BIRTHNEST=<salt>:<sealed onion>
SYVOX=<salt>
PRIVOX=<salt>
FRIVOX=<salt>:<their pubvox, sealed>     one line per friend, optional
```

Every field has its own salt, made by band80. Opening runs vox once per field with that salt and the key, and gives the result to the piece that knows the field:

| field | opened as | piece |
|---|---|---|
| ALIX | `alix.open_(vox(salt, key), sealed)` | alix |
| BIRTHNEST | `onyon.open_(vox(salt, key), sealed)` | onyon |
| SYVOX | `vox(salt, key)` | vox |
| PRIVOX | `vox(salt, key)` | vox |
| PUBVOX | X25519 of the privox | mepoid |
| FRIVOX | see Friends below | mepoid |

- **Any key opens the file into a full profile:** another alias, another valid onion, another syvox, privox and pubvox, and other friends. Only the right key gives yours. Nothing in the file says which one is right.
- **PUBVOX is never written.** It comes from PRIVOX every time. Written in clear, it would let anyone try keys until one gave the same PUBVOX.
- **The real values never touch the disk.** They live in memory while mepoid runs. (Python cannot promise to wipe memory before it ends.)
- **mepoid never writes over another file.** If the name is taken, it seals the alias again, which gives another public name. The only file it rewrites is the same `.mepo`, when you add a friend, and atomically: the old one stays whole until the new one is in.
- **The key is not checked.** There is no wrong key, so a typo opens someone else's profile without saying so. That is why create asks for it twice, and friend shows your alias and waits for a yes.

## Voices

PUBVOX is X25519 (RFC 7748) of 32 bytes taken from the privox with shake_256(`privox1|` + its 80 digits). X25519 lives in mepoid until the voices have their own library.

Don't hand out PUBVOX: give each friend their own pubvox from a FRIVOX slot. Whoever holds one of your pubvoxes and also gets your `.mepo` can try keys until one gives that same pubvox.

## Friends

Each friend has their own FRIVOX line with its own salt, so each friend gets a different pubvox from you and two friends can't tell they know the same person.

```
$ python3 mepoid.py friend new preparka.mepo
key:
ALIX       maria    is this your profile? [y/N] y
FRIVOX 1   give them: 14e9cfd16c60652c20dccc313a79ae6c49ec40e2ee48a96589d63493de0e8735

$ python3 mepoid.py friend set preparka.mepo 1 5948fa3d2e404ffc9b219070aaf9212a808ab514a673b2e4e18a7747cc6ea152
key:
ALIX       maria    is this your profile? [y/N] y
FRIVOX 1   frivox: d3989724c03b556e53f505bf0791957780b4511ced387c91b2d495e4b1cc0f15
```

`friend new` gives you the pubvox to hand that friend; `friend set` seals the one they hand you. Both sides get the same frivox. It is the seed the client (cypo) starts its ratchet from; mepoid keeps no session state.

`friend` shows your alias and waits for a yes before writing, because the key is never checked: a typo would seal the friend under someone else's profile without saying so.

| | |
|---|---|
| s | vox(salt, key) |
| your half | shake_256(`frivox1|` + the 80 digits of s), 32 bytes, as an X25519 scalar |
| mine | X25519(your half, 9): the pubvox you give that friend |
| sealed | S = P + t·B on ed25519, t = shake_256(`frisel1|` + the 80 digits of s), 64 bytes little-endian, mod ℓ, P their pubvox as an ed25519 point (y = (u−1)/(u+1), sign 0), stored as 32 bytes hex |
| theirs | u of S − t·B |
| frivox | shake_256(`frivox1-pair|` + X25519(your half, theirs) + both pubvoxes sorted), 32 bytes hex |

Their pubvox is sealed as a point, never by adding digits. Only a few percent of all 32-byte values are keys of the prime-order subgroup: sealed by digits, the right key would be the only one that opens every friend into a valid key, and the file would point at it. Sealed as a point, any key opens every friend into a valid key. The ed25519 math is onyon's, pinned by sha256.

`friend set` only accepts a pubvox in the prime-order subgroup, which every real one is.

## Limits

Any key opens the file into a full profile, so nobody can confirm a guess from the file alone. That holds until someone who has your `.mepo` also has something real of yours: one of your pubvoxes (a friend has it), your birthnest or your alias. From then on they can try keys offline, at one scrypt (64 MiB) per guess, and what protects you is the strength of your key. Use a long one.

PRIVOX is your identity, not a pod: it can't be cut. With it, someone can compute your frivoxs. The ratchet in the client is what keeps past messages safe if that happens.

## Later

`SUBS{…}` comes when the spaces exist.

## Test

```
python3 -m unittest discover test
```

Run `fetch.py` first. Includes the X25519 vector of RFC 7748, fixed answers for FRIVOX that any implementation of v1.1 must reproduce, and a check that a v1.0 file opens exactly as before.

## Licence

MIT, see `LICENSE`.

## Verify

```
sha256sum mepoid.py fetch.py
```

v1.1.0:

```
c76f1252fe90c87055c8016ba84be53becc941b870518576a6a364a3de4d47ec  mepoid.py
2dbf15427202862ed63e55c22618bb87ffbdabc63e6ee11870d4c10df46573ed  fetch.py
```
