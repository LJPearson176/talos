"""
Governed AutoGen Agents

This module demonstrates how to integrate RPN Governance 
with AutoGen agent function calls.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Callable, Dict, Any, Optional

from governance import verify_action, set_active_policy
from registry import ROLE_GUEST, ROLE_ADMIN, STANDARD_ACCESS_POLICY

# Set policy
set_active_policy(STANDARD_ACCESS_POLICY)

# --- Governance Wrapper ---

def governed_function(
    action_name: str,
    func: Callable,
    role: int = ROLE_GUEST,
    context: Optional[Dict] = None,
    gate_func: Optional[Callable] = None
) -> Callable:
    """
    Wraps a function with RPN Governance checks.
    For use with AutoGen's register_function.
    
    Args:
        action_name: The action to verify (from registry).
        func: The underlying function.
        role: Role bitmask.
        context: Additional context for RPN.
        gate_func: Optional custom gate function.
        
    Returns:
        A wrapped function that enforces governance.
    """
    context = context or {}
    
    def wrapper(*args, **kwargs) -> Any:
        # Get proof
        proof = verify_action(role, action_name, context_overrides=context)
        
        # Apply gate logic
        if gate_func:
            allowed = gate_func(proof.trace)
        else:
            allowed = proof.allowed
        
        if not allowed:
            return f"DENIED: Action '{action_name}' blocked by governance. Proof: {proof.trace}"
        
        return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    return wrapper


# --- Mock Tools ---

def deploy_to_production(version: str) -> str:
    return f"Deployed version {version} to production successfully!"

def read_configuration() -> str:
    return "Config: {'debug': False, 'env': 'production'}"


# --- Demo (Without actual LLM, just showing wrapper behavior) ---

if __name__ == "__main__":
    print("=== AutoGen Governed Functions Demo ===\n")
    print("(Note: This demo shows wrapper behavior without an actual LLM)\n")
    
    # Wrap functions
    governed_deploy_guest = governed_function(
        "SYSTEM_REBOOT",  # High risk
        deploy_to_production,
        role=ROLE_GUEST
    )
    
    governed_deploy_admin = governed_function(
        "SYSTEM_REBOOT",
        deploy_to_production,
        role=ROLE_ADMIN
    )
    
    governed_read = governed_function(
        "READ_FILE",  # Low risk
        read_configuration,
        role=ROLE_GUEST
    )
    
    # Test
    print("1. Guest tries to deploy (high risk):")
    result = governed_deploy_guest("v1.0.0")
    print(f"   Result: {result}")
    
    print("\n2. Guest tries to read config (low risk):")
    result = governed_read()
    print(f"   Result: {result}")
    
    print("\n3. Admin tries to deploy (high risk):")
    result = governed_deploy_admin("v2.0.0")
    print(f"   Result: {result}")
    
    # --- AutoGen Integration Example (Commented) ---
    # from autogen import AssistantAgent, UserProxyAgent
    #
    # assistant = AssistantAgent("assistant", llm_config={"model": "gpt-4"})
    # user_proxy = UserProxyAgent("user")
    #
    # # Register governed functions
    # user_proxy.register_for_execution(name="deploy")(
    #     governed_function("SYSTEM_REBOOT", deploy_to_production, role=ROLE_USER)
    # )
    #
    # # Now when the LLM calls "deploy", it goes through governance first
