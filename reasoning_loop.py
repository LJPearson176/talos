"""
The Reasoning Loop (The Lawyer)

This module simulates an agent that:
1. Attempts an action (gets DENIED by Iron Proxy).
2. Analyzes the Proof to understand WHY.
3. Formulates a new plan to satisfy the missing clause.
4. Retries with the new strategy.
"""

from tool_wrapper import GovernedTool
from governance import set_active_policy
from registry import EPOCH_POLICY, ROLE_GUEST, ROLE_USER, ROLE_ADMIN

# Switch to EPOCH Policy (Emergency Mode = Admin Required)
set_active_policy(EPOCH_POLICY)

# Global Epoch (simulates central state server)
GLOBAL_EPOCH = 1 # Emergency Mode

# --- Mock Tools (The "Physical" Actions) ---

def mock_deploy(code):
    """Deploys code to production."""
    print(f"  [TOOL] Deploying: '{code}'")
    return {"status": "SUCCESS", "message": "Deployed to production"}

def mock_escalate():
    """Requests privilege escalation."""
    print(f"  [TOOL] Escalation Request Submitted...")
    return {"status": "SUCCESS", "new_role": ROLE_ADMIN}

# --- The Mock LLM (Reasoning Engine) ---

def reason_about_denial(proof_trace):
    """
    Simulates an LLM analyzing a denial proof.
    Returns a "Plan" based on which clause failed.
    """
    print(f"\n[Agent LLM] Analyzing denial proof: {proof_trace}")
    
    # Check clauses in order of actionability
    is_normal = proof_trace.get("is_normal_mode", False)
    is_emergency = proof_trace.get("is_emergency_mode", False)
    is_admin = proof_trace.get("is_admin", False)
    
    if is_emergency and not is_admin:
        print("[Agent LLM] Diagnosis: Emergency Mode active, but I lack Admin privileges.")
        return {"action": "ESCALATE", "reason": "Emergency requires Admin"}
    
    if not is_admin:
        print("[Agent LLM] Diagnosis: I lack Admin privileges.")
        return {"action": "ESCALATE", "reason": "is_admin clause failed"}
    
    return {"action": "GIVE_UP", "reason": "Unknown blocking clause"}

# --- Agent State ---

class AgentState:
    def __init__(self):
        self.role = ROLE_GUEST # Start as Guest
        
    def get_context(self):
        return {"epoch": GLOBAL_EPOCH}

# --- Custom Gate Logic ---

def check_epoch_gate(proof):
    """
    Implements: Allowed if (Normal) OR (Emergency AND Admin)
    """
    trace = proof.get("proof", {})
    is_normal = trace.get("is_normal_mode", False)
    is_emergency = trace.get("is_emergency_mode", False)
    is_admin = trace.get("is_admin", False)
    
    return is_normal or (is_emergency and is_admin)

def epoch_gate_func(trace):
    """
    Custom gate function for GovernedTool.
    Implements: Allowed if (Normal) OR (Emergency AND Admin)
    Receives trace dict directly.
    """
    is_normal = trace.get("is_normal_mode", False)
    is_emergency = trace.get("is_emergency_mode", False)
    is_admin = trace.get("is_admin", False)
    
    return is_normal or (is_emergency and is_admin)

# --- The Reasoning Loop Simulation ---

def run_reasoning_loop():
    print("=" * 50)
    print("      THE REASONING LOOP SIMULATION")
    print("=" * 50)
    print(f"\n[System] Global Epoch: {GLOBAL_EPOCH} ({'EMERGENCY' if GLOBAL_EPOCH == 1 else 'NORMAL'})")
    
    agent = AgentState()
    
    # Attempt 1: Deploy as Guest in Emergency Mode
    print("\n--- Attempt 1: Deploy as Guest (Emergency Mode) ---")
    deploy_tool = GovernedTool(
        mock_deploy, 
        agent.role, 
        "NET_CONNECT", 
        agent.get_context(),
        gate_func=epoch_gate_func # Custom gate logic
    )
    result = deploy_tool.run(code="v1.0.0")
    
    # Check if it's a denial (dict with proof) or raw result
    if isinstance(result, dict) and "proof" in result:
        # Apply our custom gate logic
        allowed = check_epoch_gate(result)
        
        if not allowed:
            print(f"[Agent] Action DENIED by Iron Proxy.")
            print(f"[Agent] Proof: {result['proof']}")
            
            # --- The Feedback Loop ---
            plan = reason_about_denial(result["proof"])
            
            if plan["action"] == "ESCALATE":
                print(f"\n[Agent] New Plan: {plan['action']} ({plan['reason']})")
                
                # Attempt 2: Escalate (this is a safe action, allowed for all)
                print("\n--- Attempt 2: Request Escalation ---")
                escalate_tool = GovernedTool(mock_escalate, agent.role, "READ_FILE", {"epoch": GLOBAL_EPOCH})
                esc_result = escalate_tool.run()
                
                if isinstance(esc_result, dict) and esc_result.get("status") == "SUCCESS":
                    agent.role = esc_result["new_role"]
                    print(f"[Agent] Privilege escalated to: {agent.role} (Admin)")
                    
                    # Attempt 3: Retry Deploy as Admin
                    print("\n--- Attempt 3: Retry Deploy as Admin ---")
                    deploy_tool_admin = GovernedTool(mock_deploy, agent.role, "NET_CONNECT", agent.get_context())
                    result = deploy_tool_admin.run(code="v1.0.0")
                    
                    if isinstance(result, dict) and "proof" in result:
                        allowed = check_epoch_gate(result)
                        if allowed:
                            print("[Agent] Gate check PASSED. Deploying...")
                        else:
                            print(f"[Agent] Still DENIED! Proof: {result['proof']}")
                    else:
                        print(f"[Agent] Deployment Result: {result}")
        else:
            print(f"[Agent] Gate check PASSED. Deploying...")
    else:
        print(f"[Agent] Deployment Result: {result}")
        
    print("\n" + "=" * 50)
    print("      END OF REASONING LOOP")
    print("=" * 50)

if __name__ == "__main__":
    run_reasoning_loop()
