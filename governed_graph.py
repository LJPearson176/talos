import random
import time
from governance import Policy, verify_action, set_active_policy
from registry import EPOCH_POLICY, ROLE_GUEST, ROLE_USER, ROLE_ADMIN

# REMOVED: set_active_policy(EPOCH_POLICY) - Moved to TimeSimulation.run()

class GlobalState:
    epoch = 0 # 0=Normal, 1=Emergency

class AgentState:
    def __init__(self, role, name="Agent-001"):
        self.role = role
        self.name = name
        self.current_node = "START"
        self.history = []

    def log_transition(self, to_node, proof):
        entry = {
            "timestamp": time.time(),
            "from": self.current_node,
            "to": to_node,
            "proof": proof.to_dict(),
            "status": "APPROVED" if proof.allowed else "DENIED"
        }
        self.history.append(entry)

class Gatekeeper:
    """
    Time-Aware Gatekeeper.
    """
    
    @staticmethod
    def check_transition(state, next_node):
        print(f"\n[Gatekeeper] Intercepting: {state.current_node} -> {next_node} (Epoch: {GlobalState.epoch})")
        
        # 1. State Injection
        context_overrides = {
            "epoch": GlobalState.epoch
        }
        
        # 2. Logic Selection
        # If Emergency (Epoch 1), we enforce strict Admin check.
        # If Normal (Epoch 0), we allow Guests (mock logic: just is_normal_mode check).
        
        # Actually, the EPOCH_POLICY defines:
        # - is_normal_mode (Epoch=0)
        # - is_emergency_mode (Epoch=1)
        # - is_admin (Role & 4)
        
        # We need to construct the gate logic:
        # "Allowed if (Normal) OR (Emergency AND Admin)"
        # RPN Proof Logic:
        #   Clause A: is_normal_mode
        #   Clause B: is_emergency_mode
        #   Clause C: is_admin
        
        # Gate Logic: A OR (B AND C)
        
        proof = verify_action(state.role, "NET_CONNECT", context_overrides=context_overrides)
        # Note: action name is arbitrary here as we rely on EPOCH_POLICY clauses not Action ID.
        # But verify_action requires valid action. NET_CONNECT is fine.
        
        trace = proof.trace
        
        is_normal = trace.get("is_normal_mode", False)
        is_emergency = trace.get("is_emergency_mode", False)
        is_admin = trace.get("is_admin", False)
        
        allowed = is_normal or (is_emergency and is_admin)
        
        proof.allowed = allowed
        state.log_transition(next_node, proof)
        
        if allowed:
            print(f"  [>] APPROVED. (Normal={is_normal}, Emergency={is_emergency}, Admin={is_admin})")
            return True
        else:
            print(f"  [x] DENIED.   (Normal={is_normal}, Emergency={is_emergency}, Admin={is_admin})")
            return False

class TimeSimulation:
    def __init__(self):
        pass
        
    def run(self):
        print("=== TIME-AWARE GOVERNANCE SIMULATION ===")
        # Ensure correct policy
        set_active_policy(EPOCH_POLICY)
        
        # 1. Normal Mode (Epoch 0)
        print("\n--- Phase 1: Normal Mode (Epoch 0) ---")
        GlobalState.epoch = 0
        
        guest = AgentState(ROLE_GUEST, "Guest")
        admin = AgentState(ROLE_ADMIN, "Admin")
        
        print("Guest attempting action...")
        Gatekeeper.check_transition(guest, "CONNECT")
        
        # 2. Emergency Mode (Epoch 1)
        print("\n--- Phase 2: EMERGENCY MODE (Epoch 1) ---")
        GlobalState.epoch = 1
        
        print("Guest attempting action...")
        Gatekeeper.check_transition(guest, "CONNECT")
        
        print("Admin attempting action...")
        Gatekeeper.check_transition(admin, "CONNECT")

if __name__ == "__main__":
    sim = TimeSimulation()
    sim.run()
