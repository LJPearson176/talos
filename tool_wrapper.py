
from governance import verify_action
from registry import ACTIONS

class GovernedTool:
    """
    The Iron Proxy (Jailer).
    Wraps any function and enforces RPN governance policies before execution.
    """
    def __init__(self, tool_func, role_mask, action_name, context_overrides=None, gate_func=None):
        self.tool = tool_func
        self.role_mask = role_mask
        self.action_name = action_name
        self.context_overrides = context_overrides or {}
        self.gate_func = gate_func # Optional custom gate function
        
    def run(self, **kwargs):
        # 1. Ask the Constable (Kernel)
        proof = verify_action(self.role_mask, self.action_name, context_overrides=self.context_overrides)
        
        # 2. Determine Allowed Status
        if self.gate_func:
            # Apply custom gate logic to the proof trace
            allowed = self.gate_func(proof.trace)
        else:
            # Use policy's built-in combination logic
            allowed = proof.allowed
        
        # 3. Enforce Decision
        if not allowed:
            # RETURN THE PROOF TO THE AGENT
            # This is the feedback loop mechanism
            return {
                "status": "DENIED",
                "error": "Governance Policy Failed",
                "proof": proof.trace, # The "Why"
                "policy": proof.policy_name
            }
            
        # 4. Execute only if allowed
        print(f"[IronProxy] Allowed: {self.action_name}")
        return self.tool(**kwargs)
