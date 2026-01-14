
from crypto_governance import CryptoGovernance
from registry import ROLE_ADMIN, ROLE_GUEST
import time

def run_demo():
    print("=== Zero-Knowledge Authority Demo ===\n")
    
    # 1. Initialize Controller (Verifies Manifest on Boot)
    gov = CryptoGovernance()
    
    print("\n--- 1. Agent Request: Guest tries 'DELETE_DB' ---")
    warrant = gov.verify_action(
        agent_id="Agent_007",
        action="DELETE_DB",
        role_mask=ROLE_GUEST
    )
    
    print(f"Received Warrant: {warrant}")
    print(f"Warrant Valid? {warrant.is_valid(gov.constable_pub)}")
    if not warrant.allowed:
        print(">> ACCESS DENIED (As expected)")
        
    print("\n--- 2. Agent Request: Admin tries 'DEPLOY' ---")
    warrant_admin = gov.verify_action(
        agent_id="Admin_Alpha",
        action="DEPLOY",
        role_mask=ROLE_ADMIN
    )
    
    print(f"Received Warrant: {warrant_admin}")
    print(f"Warrant Valid? {warrant_admin.is_valid(gov.constable_pub)}")
    
    if warrant_admin.allowed:
        print(">> WARRANT GRANTED. PROCEEDING.")
        # Simulating Tool Execution using Warrant
        execute_tool(warrant_admin)
        
    print("\n--- 3. Tampering Test ---")
    # Simulate tampering with the warrant signature
    fake_sig = warrant_admin.signature[:-2] + "00"
    warrant_admin.signature = fake_sig
    valid = warrant_admin.is_valid(gov.constable_pub)
    print(f"Tampered Warrant Valid? {valid}")

def execute_tool(warrant):
    print(f"[Tool] Verifying Warrant for {warrant.action}...")
    # In reality, tool would fetch public key from secure config
    if warrant.allowed:
        print("[Tool] Signature Verified. Executing Action...")
    else:
        print("[Tool] STOP. Warrant denies action.")

if __name__ == "__main__":
    run_demo()
