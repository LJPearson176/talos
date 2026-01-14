"""
Governed LangChain Tools

This module provides a factory for creating LangChain Tool objects 
that are wrapped with RPN Governance checks.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, Callable, Any, Dict

from governance import verify_action, set_active_policy
from registry import ROLE_GUEST, ROLE_USER, ROLE_ADMIN, STANDARD_ACCESS_POLICY, EPOCH_POLICY

# Factory

def create_governed_tool(
    name: str,
    func: Callable,
    action_name: str,
    description: str,
    args_schema: Optional[BaseModel] = None,
    role: int = ROLE_GUEST,
    context: Optional[Dict] = None,
    gate_func: Optional[Callable] = None
) -> StructuredTool:
    """
    Creates a LangChain StructuredTool with RPN Governance enforcement.
    
    Args:
        name: Tool name (for LangChain).
        func: The underlying function to call.
        action_name: The action name for the governance check (from registry).
        description: Tool description (for LangChain).
        args_schema: Optional Pydantic model for tool arguments.
        role: The role bitmask of the calling agent.
        context: Additional context for RPN evaluation.
        gate_func: Optional custom gate function (trace -> bool).
        
    Returns:
        A LangChain StructuredTool that enforces governance.
    """
    
    context = context or {}
    
    def governed_func(**kwargs) -> Any:
        # Pop role override if present
        current_role = kwargs.pop("role", role)
        current_context = kwargs.pop("context", context)
        
        # Get proof from Constable
        proof = verify_action(current_role, action_name, context_overrides=current_context)
        
        # Apply gate logic
        if gate_func:
            allowed = gate_func(proof.trace)
        else:
            allowed = proof.allowed
        
        if not allowed:
            return {
                "status": "DENIED",
                "error": "Governance Policy Failed",
                "proof": proof.trace,
                "policy": proof.policy_name
            }
        
        # Execute
        return func(**kwargs)
    
    return StructuredTool.from_function(
        name=name,
        func=governed_func,
        description=description,
        args_schema=args_schema
    )


# --- Example Usage (Mock Tools) ---

class DeployArgs(BaseModel):
    code_version: str = Field(description="Version of code to deploy")

def deploy_code(code_version: str) -> dict:
    return {"status": "SUCCESS", "deployed": code_version}

def read_data() -> dict:
    return {"status": "SUCCESS", "data": [1, 2, 3]}


# --- Demo ---

if __name__ == "__main__":
    print("=== LangChain Governed Tools Demo ===\n")
    
    # Set policy
    set_active_policy(STANDARD_ACCESS_POLICY)
    
    # Create tools
    deploy_tool = create_governed_tool(
        name="deploy",
        func=deploy_code,
        action_name="SYSTEM_REBOOT",  # High risk
        description="Deploy code to production",
        args_schema=DeployArgs,
        role=ROLE_GUEST
    )
    
    read_tool = create_governed_tool(
        name="read_data",
        func=read_data,
        action_name="READ_FILE",  # Low risk
        description="Read data from storage",
        role=ROLE_GUEST
    )
    
    # Test
    print("1. Guest tries to deploy (high risk action):")
    result = deploy_tool.invoke({"code_version": "v1.0.0"})
    print(f"   Result: {result}")
    
    print("\n2. Guest tries to read (low risk action):")
    result = read_tool.invoke({})
    print(f"   Result: {result}")
    
    print("\n3. Admin tries to deploy:")
    deploy_admin = create_governed_tool(
        name="deploy_admin",
        func=deploy_code,
        action_name="SYSTEM_REBOOT",
        description="Deploy code to production",
        args_schema=DeployArgs,
        role=ROLE_ADMIN
    )
    result = deploy_admin.invoke({"code_version": "v2.0.0"})
    print(f"   Result: {result}")
