import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import alix  # noqa: E402
import band80  # noqa: E402
import mepoid  # noqa: E402
import onyon  # noqa: E402

FIXED_SEALED = "5fee09a684d5683bda105b9b798237861f54c417a5d496b652f2275b306e6cda"
FIXED_FRIVOX = "98b88aa16e3f20b367182108fa5491dec7e8ae9a4a4fd9f686ee26bafda8b783"
ONION = "duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion"


class TestX25519(unittest.TestCase):
    def test_rfc7748(self):
        k = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
        self.assertEqual(mepoid._x25519(k, 9).to_bytes(32, "little").hex(),
                         "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a")

    def test_both_sides_get_the_same_secret(self):
        a, b = os.urandom(32), os.urandom(32)
        pa, pb = mepoid._x25519(a, 9), mepoid._x25519(b, 9)
        self.assertEqual(mepoid._x25519(a, pb), mepoid._x25519(b, pa))


class TestMepoid(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.path = mepoid.create(self.d.name, "maria", ONION, "holamundo")

    def tearDown(self):
        self.d.cleanup()

    def test_named_after_the_public_alias(self):
        name = os.path.basename(self.path)
        sealed = open(self.path).read().split("ALIX=")[1].split("\n")[0].split(":")[1]
        self.assertEqual(name, alix.show(sealed) + ".mepo")

    def test_right_key_gives_the_profile(self):
        p = mepoid.open_(self.path, "holamundo")
        self.assertEqual(p["ALIX"], "maria")
        self.assertEqual(p["BIRTHNEST"], ONION)
        self.assertEqual(p["PUBVOX"], mepoid.pubvox(p["PRIVOX"]))

    def test_any_key_gives_a_full_valid_profile(self):
        real = mepoid.open_(self.path, "holamundo")
        for key in ("pedro", "", "Holamundo"):
            p = mepoid.open_(self.path, key)
            self.assertTrue(alix.proper(p["ALIX"]))
            onyon.parse(p["BIRTHNEST"])
            for f in mepoid.FIELDS + ("PUBVOX",):
                self.assertNotEqual(p[f], real[f], f)

    def test_file_holds_nothing_real(self):
        text = open(self.path).read()
        real = mepoid.open_(self.path, "holamundo")
        for f in ("BIRTHNEST", "SYVOX", "PRIVOX", "PUBVOX"):
            self.assertNotIn(real[f], text)
        self.assertNotIn("PUBVOX", text)

    def test_never_writes_over_a_file(self):
        before = set(os.listdir(self.d.name))
        p2 = mepoid.create(self.d.name, "maria", ONION, "holamundo")
        self.assertNotIn(os.path.basename(p2), before)
        self.assertEqual(len(os.listdir(self.d.name)), 2)

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            mepoid.create(self.d.name, "qqqq", ONION, "k")
        with self.assertRaises(ValueError):
            mepoid.create(self.d.name, "maria", "nope.onion", "k")


class TestFriends(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.a = mepoid.create(self.d.name, "maria", ONION, "holamundo")
        self.b = mepoid.create(self.d.name, "pedro", ONION, "otraclave")
        na, self.mine_a = mepoid.friend_new(self.a, "holamundo")
        nb, self.mine_b = mepoid.friend_new(self.b, "otraclave")
        self.fa = mepoid.friend_set(self.a, na, self.mine_b, "holamundo")
        self.fb = mepoid.friend_set(self.b, nb, self.mine_a, "otraclave")

    def tearDown(self):
        self.d.cleanup()

    def test_both_friends_get_the_same_frivox(self):
        self.assertEqual(self.fa, self.fb)
        self.assertEqual(len(self.fa), 64)

    def test_open_gives_the_friends_back(self):
        fr = mepoid.open_(self.a, "holamundo")["FRIVOXS"]
        self.assertEqual(fr, [{"MINE": self.mine_a, "THEIRS": self.mine_b, "FRIVOX": self.fa}])

    def test_old_fields_do_not_change(self):
        p = mepoid.open_(self.a, "holamundo")
        self.assertEqual((p["ALIX"], p["BIRTHNEST"]), ("maria", ONION))

    def test_one_pubvox_per_friend(self):
        n, mine2 = mepoid.friend_new(self.a, "holamundo")
        self.assertEqual(n, 2)
        self.assertNotEqual(mine2, self.mine_a)
        self.assertNotEqual(mine2, mepoid.open_(self.a, "holamundo")["PUBVOX"])

    def test_file_holds_no_friend_in_clear(self):
        text = open(self.a).read()
        for v in (self.mine_a, self.mine_b, self.fa):
            self.assertNotIn(v, text)

    def test_any_key_opens_every_friend_into_a_valid_pubvox(self):
        # the twist leak: with digit sealing about half of these would not be on the curve
        for _ in range(3):
            mepoid.friend_set(self.a, mepoid.friend_new(self.a, "holamundo")[0],
                              mepoid.pubvox(band80.gen(4, 20)), "holamundo")
        for key in ("pedro", "", "Holamundo", "x" * 40):
            for fr in mepoid.open_(self.a, key)["FRIVOXS"]:
                mepoid._to_point(fr["THEIRS"])
                self.assertNotEqual(fr["FRIVOX"], self.fa)

    def test_seal_and_open_undo_each_other(self):
        for _ in range(20):
            s, pub = band80.gen(4, 20), mepoid.pubvox(band80.gen(4, 20))
            self.assertEqual(mepoid._open_pub(s, mepoid._seal_pub(s, pub)), pub)

    def test_fixed_answer(self):
        # any implementation of v1.1 must give these
        s = "1" * 80
        pub = mepoid.pubvox("2" * 80)
        self.assertEqual(mepoid._seal_pub(s, pub), FIXED_SEALED)
        self.assertEqual(mepoid._frivox(mepoid._mine(s), mepoid._x25519(mepoid._mine(s), 9).to_bytes(32, "little").hex(), pub), FIXED_FRIVOX)

    def test_rejects_what_is_not_a_pubvox(self):
        twist = next(u for u in range(2, 200)
                     if onyon._decode(((u - 1) * pow(u + 1, mepoid._P - 2, mepoid._P) % mepoid._P).to_bytes(32, "little")) is None)
        for bad in ("zz", "00" * 31, "00" * 32, twist.to_bytes(32, "little").hex()):
            with self.assertRaises(ValueError):
                mepoid.friend_set(self.a, 1, bad, "holamundo")
        with self.assertRaises(ValueError):
            mepoid.friend_set(self.a, 9, self.mine_b, "holamundo")

    def test_rewrite_is_atomic_and_keeps_the_name(self):
        self.assertEqual(sorted(os.listdir(self.d.name)), sorted(map(os.path.basename, (self.a, self.b))))

    def test_a_v1_0_file_still_opens(self):
        lines = [l for l in open(self.a).read().splitlines() if not l.startswith("FRIVOX=")]
        old = os.path.join(self.d.name, "old.mepo")
        open(old, "w").write("\n".join(lines) + "\n")
        p = mepoid.open_(old, "holamundo")
        self.assertEqual((p["ALIX"], p["FRIVOXS"]), ("maria", []))


class TestFetch(unittest.TestCase):
    def test_refuses_a_file_that_does_not_match(self):
        import fetch
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(fetch.fetch(d, get=lambda url: b"not the real file"))
            self.assertEqual(os.listdir(d), [])

    def test_keeps_files_that_match(self):
        import fetch
        with tempfile.TemporaryDirectory() as d:
            for _, name, _ in fetch.PIECES:
                with open(os.path.join(mepoid.HERE, name), "rb") as src, open(os.path.join(d, name), "wb") as dst:
                    dst.write(src.read())
            self.assertTrue(fetch.fetch(d, get=lambda url: self.fail("should not download")))


if __name__ == "__main__":
    unittest.main()
