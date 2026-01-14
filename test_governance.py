import unittest
from governance import verify_action
from registry import ROLE_GUEST, ROLE_USER, ROLE_ADMIN, STANDARD_ACCESS_POLICY

class TestConstable(unittest.TestCase):
    
    def setUp(self):
        # Reset to Standard Policy before each test
        from governance import set_active_policy
        set_active_policy(STANDARD_ACCESS_POLICY)
    
    def test_guest_permissions(self):
        # Guest (1) should allow READ_FILE (101 < 200)
        proof = verify_action(ROLE_GUEST, "READ_FILE")
        self.assertTrue(proof.allowed, "Guest should be able to READ_FILE")
        self.assertEqual(proof.policy_name, "StandardAccess")
        # Proof Verification
        # is_admin should be False, is_safe_action should be True
        self.assertFalse(proof.trace["is_admin"], "Guest is NOT admin")
        self.assertTrue(proof.trace["is_safe_action"], "READ_FILE is safe")
        
        # Guest (1) should DENY DELETE_FILE (202 > 200)
        proof = verify_action(ROLE_GUEST, "DELETE_FILE")
        self.assertFalse(proof.allowed, "Guest should NOT be able to DELETE_FILE")
        # Proof Verification
        self.assertFalse(proof.trace["is_admin"])
        self.assertFalse(proof.trace["is_safe_action"])
        
        print(f"\n[Test] Guest Logic Proof: {proof}")

    def test_admin_permissions(self):
        # Admin (4) should allow EVERYTHING
        proof = verify_action(ROLE_ADMIN, "DELETE_FILE")
        self.assertTrue(proof.allowed, "Admin should be able to DELETE_FILE")
        # Proof Verification: is_admin=True, is_safe_action=False (202 not < 200)
        self.assertTrue(proof.trace["is_admin"], "Admin check passed")
        self.assertFalse(proof.trace["is_safe_action"], "Action is unsafe")
        
        print(f"\n[Test] Admin Logic Proof: {proof}")

    def test_unknown_action(self):
        # Fail Closed on unknown ID
        proof = verify_action(ROLE_ADMIN, "LAUNCH_NUKES")
        self.assertFalse(proof.allowed, "Unknown action should default to Deny")
        self.assertIn("Unknown", proof.policy_name)
        
    def test_epoch_logic(self):
        from governance import set_active_policy
        from registry import EPOCH_POLICY
        
        # Switch to Epoch Policy
        set_active_policy(EPOCH_POLICY)
        
        # 1. Normal Mode (Epoch 0)
        # Should allow Guest (is_normal_mode=True)
        proof = verify_action(ROLE_GUEST, "NET_CONNECT", context_overrides={"epoch": 0})
        is_normal = proof.trace.get("is_normal_mode")
        self.assertTrue(is_normal, "Epoch 0 should be normal mode")
        
        # 2. Emergency Mode (Epoch 1)
        # Should deny Guest (is_normal=False, is_admin=False)
        proof = verify_action(ROLE_GUEST, "NET_CONNECT", context_overrides={"epoch": 1})
        self.assertFalse(proof.trace.get("is_normal_mode"), "Epoch 1 is NOT normal")
        self.assertTrue(proof.trace.get("is_emergency_mode"), "Epoch 1 IS emergency")
        self.assertFalse(proof.trace.get("is_admin"), "Guest is NOT admin")
        
        # 3. Emergency Mode (Epoch 1) + Admin
        # Should verify Admin clause
        proof = verify_action(ROLE_ADMIN, "NET_CONNECT", context_overrides={"epoch": 1})
        self.assertTrue(proof.trace.get("is_admin"), "Admin check passed")

if __name__ == '__main__':
    print("=== Constable Governance Verification (Legibile Mode) ===")
    unittest.main()
