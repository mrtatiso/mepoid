import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import alix  # noqa: E402
import mepoid  # noqa: E402
import onyon  # noqa: E402

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
