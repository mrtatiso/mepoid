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
```

The key is asked without showing it, twice when creating. From a script it can come through stdin.

### Python

```python
import mepoid

path = mepoid.create(".", "maria", birthnest, key)    # → "./preparka.mepo"
profile = mepoid.open_(path, key)                       # → dict, in memory only
```

## The .mepo

Named after the alias anyone sees, so the name says nothing either. Inside, only band80s and a sealed onion:

```
mepoid/1
ALIX=<salt>:<sealed alias>
BIRTHNEST=<salt>:<sealed onion>
SYVOX=<salt>
PRIVOX=<salt>
```

Every field has its own salt, made by band80. Opening runs vox once per field with that salt and the key, and gives the result to the piece that knows the field:

| field | opened as | piece |
|---|---|---|
| ALIX | `alix.open_(vox(salt, key), sealed)` | alix |
| BIRTHNEST | `onyon.open_(vox(salt, key), sealed)` | onyon |
| SYVOX | `vox(salt, key)` | vox |
| PRIVOX | `vox(salt, key)` | vox |
| PUBVOX | X25519 of the privox | mepoid |

- **Any key opens the file into a full profile:** another alias, another valid onion, another syvox, privox and pubvox. Only the right key gives yours. Nothing in the file says which one is right.
- **PUBVOX is never written.** It comes from PRIVOX every time. Written in clear, it would let anyone try keys until one gave the same PUBVOX.
- **The real values never touch the disk.** They live in memory while mepoid runs. (Python cannot promise to wipe memory before it ends.)
- **mepoid never writes over a file.** If the name is taken, it seals the alias again, which gives another public name.
- **The key is not checked.** There is no wrong key, so a typo opens someone else's profile without saying so. That is why create asks for it twice.

## Voices

PUBVOX is X25519 (RFC 7748) of 32 bytes taken from the privox with shake_256(`privox1|` + its 80 digits). Two people who know each other's PUBVOX get the same shared secret without sending it: that is what FRIVOXS will use. X25519 lives in mepoid until the voices have their own library.

## Later

`FRIVOXS{…}` and `SUBS{…}` come when the pieces that use them exist: friends need the exchange of PUBVOX, and subscriptions the spaces.

## Test

```
python3 -m unittest discover test
```

Run `fetch.py` first. Includes the X25519 vector of RFC 7748.

## Licence

MIT, see `LICENSE`.

## Verify

```
sha256sum mepoid.py fetch.py
```

v1.0.0:

```
ddf7f94b6c7d5de3c0a8b126b9166debdb97fd34dc08b3383d5aecf196e5f430  mepoid.py
2dbf15427202862ed63e55c22618bb87ffbdabc63e6ee11870d4c10df46573ed  fetch.py
```
