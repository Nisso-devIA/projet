#!/usr/bin/env python3
import unittest

from annonce_access import OWNER_ID, ROLE_OMBRE_ID, ROLE_SENTINELLE_ID, can_use_annonce


class AnnounceAccessTests(unittest.TestCase):
    def test_owner_sentinelle_and_ombre_only(self):
        self.assertTrue(can_use_annonce(OWNER_ID, []))
        self.assertTrue(can_use_annonce(1, [ROLE_SENTINELLE_ID]))
        self.assertTrue(can_use_annonce(2, [ROLE_OMBRE_ID]))
        self.assertFalse(can_use_annonce(3, [1569739962184892597]))
        self.assertFalse(can_use_annonce(4, []))


if __name__ == "__main__":
    unittest.main()
