import logging
import time
from crypto_governance import CryptoGovernance
from governance_crypto import Warrant
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("SOCSim")

class SOCAgent:
    def __init__(self, name):
        self.name = name
        self.sk = SigningKey.generate()
        self.vk = self.sk.verify_key
        self.vk_hex = self.vk.encode(encoder=HexEncoder).decode()
        logger.info(f"[{name}] Online. KeyID: {self.vk_hex[:8]}...")

    def sign_request(self, context_str: str) -> str:
        """Sign the context string (e.g. 'severity:82')"""
        return self.sk.sign(context_str.encode()).signature.hex()

class SOCCostable(CryptoGovernance):
    """
    Specialized Constable for SOC.
    Verifies signatures against known agents and injects 'investigator_sig'/'human_sig' flags.
    """
    def __init__(self, investigator_vk, human_vk):
        super().__init__()
        self.investigator_vk = investigator_vk
        self.human_vk = human_vk
    def verify_signatures(self, context, signatures):
        """
        Verify incoming signatures and map them to RPN boolean flags.
        """
        # Default flags to 0 (False)
        context['investigator_sig'] = "0"
        context['human_sig'] = "0"
        
        # Canonical logic string for signing consistency
        msg = f"{context['severity']}"
        
        for name, sig_hex in signatures.items():
            try:
                if name == "Investigator":
                    self.investigator_vk.verify(msg.encode(), bytes.fromhex(sig_hex))
                    context['investigator_sig'] = "1"
                elif name == "Human":
                    self.human_vk.verify(msg.encode(), bytes.fromhex(sig_hex))
                    context['human_sig'] = "1"
            except Exception as e:
                logger.warning(f"[Constable] Signature verification failed for {name}: {e}")

    def verify_soc_action(self, policy_name, context):
        """
        Specialized verification for SOC policies.
        """
        if policy_name not in self.policies:
            print(f"[Constable] Policy {policy_name} not found.")
            return None
            
        policy = self.policies[policy_name]
        proof = policy.evaluate(context)
        print(f"[Debug] Evaluated Clause Trace: {proof.trace}")
        
        # Log decision
        self.logger.log_decision(
            agent_id="SOC_System",
            policy_name=policy_name,
            inputs=context,
            result_bool=proof.allowed,
            trace=proof.trace
        )
        
        # Issue Warrant
        self.nonce += 1
        return Warrant.create(
            self.constable_priv,
            "SOC_ESCALATION",
            "SOC_System",
            allowed=proof.allowed,
            timestamp=time.time(),
            nonce=self.nonce,
            ttl=60
        )

def run_simulation():
    print("=== Autonomous SOC Governance Simulation ===\n")
    
    # 1. Init Agents
    investigator = SOCAgent("Investigator")
    human = SOCAgent("Human")
    
    # 2. Init Constable (Policies loaded automatically in __init__)
    constable = SOCCostable(investigator.vk, human.vk)
    
    # Scenario 1: High Severity (82) - Solo Attempt
    severity = 82
    print(f"\n>>> SCENARIO 1: Severity {severity} (Remediation). Investigator Acting Solo.")
    
    # Sign Request
    sig_inv = investigator.sign_request(str(severity))
    
    # Dispatch to Constable
    context = {"severity": str(severity)}
    signatures = {"Investigator": sig_inv}
    
    print(f"[Investigator] Requesting Remediation. Sig: {sig_inv[:8]}...")
    
    # Verify Signatures & Inject Flags
    constable.verify_signatures(context, signatures)
    
    # Request Warrant
    warrant = constable.verify_soc_action("SOCMatrix", context)
    
    if warrant and warrant.allowed: # Check verify_soc_action returns a valid ALLOWED warrant
         print(f"[Constable] GRANTED. Warrant: {str(warrant.to_dict())[:60]}...")
    else:
         proof = constable.policies["SOCMatrix"].evaluate(context) # Re-evaluate to get trace if warrant is None? 
         # Wait, verify_soc_action calls evaluate. But it returns warrant. 
         # Wait, verify_soc_action returns a Warrant (allowed=True/False).
         # But Warrant object doesn't have 'trace' attribute? 
         # MerkleLogger logs it. 
         # I should update verify_soc_action to maybe attach trace to proper return or print it.
         print(f"[Constable] DENIED. (See log for trace)")

    # Scenario 2: High Severity (82) - Dual Attempt
    print(f"\n>>> SCENARIO 2: Escalated to Human. Dual Signature.")
    
    # Human Co-Sign
    print("[Human] Reviewing... Looks correct. Signing.")
    sig_human = human.sign_request(str(severity))
    
    signatures["Human"] = sig_human
    
    # Verify again
    constable.verify_signatures(context, signatures)
    
    # Request Warrant
    warrant = constable.verify_soc_action("SOCMatrix", context)
    
    if warrant and warrant.allowed:
         print(f"[Constable] GRANTED. Warrant: {str(warrant.to_dict())[:100]}...")
         print("[RemediationAgent] Executing 'Rotate Credentials'...")
    else:
         print(f"[Constable] DENIED. Trace: {warrant.trace if hasattr(warrant, 'trace') else 'N/A'}")

    # Scenario 3: Kill Switch (99)
    print(f"\n>>> SCENARIO 3: Kill Switch Event (Severity 99).")
    severity = 99
    context = {"severity": str(severity)}
    
    # Both sign (Desperate attempt)
    sig_inv_99 = investigator.sign_request(str(severity))
    sig_human_99 = human.sign_request(str(severity))
    signatures = {"Investigator": sig_inv_99, "Human": sig_human_99}
    
    constable.verify_signatures(context, signatures)
    warrant = constable.verify_soc_action("SOCMatrix", context)
    
    if warrant and warrant.allowed:
        print("[Constable] GRANTED (Unexpected!)")
    else:
        print("[Constable] DENIED. Kill Switch Activated.")

if __name__ == "__main__":
    run_simulation()
