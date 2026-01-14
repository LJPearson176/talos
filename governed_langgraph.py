"""
Governed LangGraph StateGraph

This module demonstrates how to integrate RPN Governance 
as a checkpoint node within a LangGraph StateGraph.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END

from governance import verify_action, set_active_policy
from registry import ROLE_GUEST, ROLE_ADMIN, EPOCH_POLICY

# Set epoch policy
set_active_policy(EPOCH_POLICY)

# --- State Schema ---

class AgentState(TypedDict):
    role: int
    epoch: int
    pending_action: str
    result: Optional[Any]
    blocked: bool
    block_reason: Optional[dict]
    last_proof: Optional[dict]

# --- Graph Nodes ---

def plan_node(state: AgentState) -> AgentState:
    """Agent plans to take an action."""
    print(f"[Plan] Planning action: {state['pending_action']}")
    return state

def governance_checkpoint(state: AgentState) -> AgentState:
    """The RPN Governance Checkpoint. Blocks if not allowed."""
    context = {"epoch": state["epoch"]}
    proof = verify_action(state["role"], state["pending_action"], context_overrides=context)
    
    # Apply epoch gate logic: Normal OR (Emergency AND Admin)
    trace = proof.trace
    is_normal = trace.get("is_normal_mode", False)
    is_emergency = trace.get("is_emergency_mode", False)
    is_admin = trace.get("is_admin", False)
    
    allowed = is_normal or (is_emergency and is_admin)
    
    state["last_proof"] = proof.trace
    
    if not allowed:
        print(f"[Governance] BLOCKED: {proof.trace}")
        state["blocked"] = True
        state["block_reason"] = proof.trace
    else:
        print(f"[Governance] ALLOWED: {proof.trace}")
        state["blocked"] = False
        state["block_reason"] = None
        
    return state

def execute_node(state: AgentState) -> AgentState:
    """Execute the action (only reached if governance passed)."""
    print(f"[Execute] Action executed successfully!")
    state["result"] = {"status": "SUCCESS", "action": state["pending_action"]}
    return state

def blocked_node(state: AgentState) -> AgentState:
    """Handle blocked state."""
    print(f"[Blocked] Action was denied. Reason: {state['block_reason']}")
    state["result"] = {"status": "DENIED", "reason": state["block_reason"]}
    return state

# --- Conditional Edge ---

def route_after_governance(state: AgentState) -> str:
    if state.get("blocked"):
        return "blocked"
    return "execute"

# --- Build Graph ---

def build_governed_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("plan", plan_node)
    graph.add_node("governance", governance_checkpoint)
    graph.add_node("execute", execute_node)
    graph.add_node("blocked", blocked_node)
    
    # Add edges
    graph.set_entry_point("plan")
    graph.add_edge("plan", "governance")
    graph.add_conditional_edges("governance", route_after_governance)
    graph.add_edge("execute", END)
    graph.add_edge("blocked", END)
    
    return graph.compile()


# --- Demo ---

if __name__ == "__main__":
    print("=== LangGraph Governed StateGraph Demo ===\n")
    
    app = build_governed_graph()
    
    # Scenario 1: Guest in Emergency Mode
    print("--- Scenario 1: Guest (Emergency Mode) ---")
    result = app.invoke({
        "role": ROLE_GUEST,
        "epoch": 1,  # Emergency
        "pending_action": "NET_CONNECT",
        "result": None,
        "blocked": False,
        "block_reason": None,
        "last_proof": None
    })
    print(f"Final State: {result['result']}\n")
    
    # Scenario 2: Admin in Emergency Mode
    print("--- Scenario 2: Admin (Emergency Mode) ---")
    result = app.invoke({
        "role": ROLE_ADMIN,
        "epoch": 1,  # Emergency
        "pending_action": "NET_CONNECT",
        "result": None,
        "blocked": False,
        "block_reason": None,
        "last_proof": None
    })
    print(f"Final State: {result['result']}\n")
    
    # Scenario 3: Guest in Normal Mode
    print("--- Scenario 3: Guest (Normal Mode) ---")
    result = app.invoke({
        "role": ROLE_GUEST,
        "epoch": 0,  # Normal
        "pending_action": "NET_CONNECT",
        "result": None,
        "blocked": False,
        "block_reason": None,
        "last_proof": None
    })
    print(f"Final State: {result['result']}\n")
