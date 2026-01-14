
import json
import time
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
from crypto_governance import CryptoGovernance
from registry import ROLE_USER

# --- 1. The Treasury Constable (Middleware) ---
class TreasuryConstable(CryptoGovernance):
    def __init__(self, agent_registry):
        super().__init__()
        self.agent_registry = agent_registry # {agent_name: verify_key_hex}

    def request_warrant(self, intent, signatures):
        """
        Verifies signatures and routes to Treasury Policy.
        intent: dict {"action": "buy_btc", "amount": 50000}
        signatures: list of (agent_name, sig_hex)
        """
        intent_bytes = json.dumps(intent, sort_keys=True).encode()
        
        # 1. Verify Signatures & Map to Context Flags
        context = {
            "amount": str(intent['amount']),
            "alpha_verified": "0",
            "beta_verified": "0"
        }
        
        # Check Signature Validity
        valid_signers = []
        for agent_name, sig_hex in signatures:
            if agent_name not in self.agent_registry:
                continue
            
            vk_hex = self.agent_registry[agent_name]
            vk = VerifyKey(vk_hex, encoder=HexEncoder)
            try:
                vk.verify(intent_bytes, bytes.fromhex(sig_hex))
                valid_signers.append(agent_name)
            except:
                print(f"[Constable] Invalid Signature from {agent_name}")
        
        # Map verified identities to policy flags
        if "Alpha" in valid_signers:
            context["alpha_verified"] = "1"
        if "Beta" in valid_signers:
            context["beta_verified"] = "1"
            
        print(f"[Constable] Context Derived: {context}")
        
        # 2. Invoke Kernel (TreasuryGuard_v1)
        # Using ROLE_USER as placeholder, logic depends on verified flags
        trace = self._invoke_policy("TreasuryGuard_v1", ROLE_USER, context)
        
        # 3. Return Result
        if trace['allowed']:
             warrant = self._issue_warrant(intent['action'], "Treasury", True)
             return {"status": "ALLOWED", "warrant": warrant, "trace": trace['trace']}
        else:
             return {"status": "DENIED", "trace": trace['trace'], "reason": "Policy failed."}

    def _invoke_policy(self, policy_name, role_mask, context):
        # Internal helper to piggyback on CryptoGovernance structure
        # We manually construct the proof since verify_action is a bit specific
        policy = self.policies[policy_name]
        proof = policy.evaluate(context)
        
        # Log to Merkle Chain
        self.logger.log_decision(
            agent_id="Treasury",
            policy_name=policy_name,
            inputs=context,
            result_bool=proof.allowed,
            trace=proof.trace
        )
        return {"allowed": proof.allowed, "trace": proof.trace}
        
    def _issue_warrant(self, action, agent_id, allowed):
        from governance_crypto import Warrant
        return Warrant.create(
            self.constable_priv, action, agent_id, allowed, time.time()
        ).to_dict()

# --- 2. The Agents ---
class TradingAgent:
    def __init__(self, name, partner=None):
        self.name = name
        self.sk = SigningKey.generate()
        self.vk = self.sk.verify_key
        self.vk_hex = self.vk.encode(encoder=HexEncoder).decode()
        self.partner = partner
        self.constable = None # Set later

    def sign(self, intent):
        msg = json.dumps(intent, sort_keys=True).encode()
        return (self.name, self.sk.sign(msg).signature.hex())

    def attempt_trade(self, amount):
        print(f"\n[{self.name}] Attempting trade: ${amount}")
        intent = {"action": "buy_btc", "amount": amount}
        
        # 1. Solo Attempt
        my_sig = self.sign(intent)
        print(f"[{self.name}] Requesting Solo Warrant...")
        response = self.constable.request_warrant(intent, [my_sig])
        
        if response['status'] == "ALLOWED":
            print(f"[{self.name}] 🟢 EXECUTION SUCCESS. Solo Trade Approved.")
            return
            
        print(f"[{self.name}] Solo failed: {response['trace']}")
        
        # 2. Escalate?
        if self.partner:
            print(f"[{self.name}] Escalating to Risk Officer ({self.partner.name})...")
            partner_sig = self.partner.review_and_sign(intent)
            
            if partner_sig:
                print(f"[{self.name}] Co-signature acquired. Retrying...")
                response = self.constable.request_warrant(intent, [my_sig, partner_sig])
                
                if response['status'] == "ALLOWED":
                    print(f"[{self.name}] 🟢 EXECUTION SUCCESS. Dual-Sig Trade Approved.")
                else:
                    print(f"[{self.name}] 🔴 FAILS EVEN WITH DUAL SIG. (Circuit Breaker?)")
            else:
                print(f"[{self.name}] Partner Refused.")
        else:
            print(f"[{self.name}] No partner. Abort.")

class RiskAgent:
    def __init__(self, name):
        self.name = name
        self.sk = SigningKey.generate()
        self.vk = self.sk.verify_key
        self.vk_hex = self.vk.encode(encoder=HexEncoder).decode()

    def sign(self, intent):
        msg = json.dumps(intent, sort_keys=True).encode()
        return (self.name, self.sk.sign(msg).signature.hex())

    def review_and_sign(self, intent):
        # Internal Risk Logic
        if intent['amount'] > 200000: # Beta's Soft Limit
            print(f"[{self.name}] REJECTED. ${intent['amount']} is excessive risk.")
            return None
        print(f"[{self.name}] APPROVED. Validating exposure... OK.")
        return self.sign(intent)

# --- 3. Simulation ---
def run_simulation():
    print("=== Two-Key Turn Treasury Simulation ===\n")
    
    # Setup Agents
    beta = RiskAgent("Beta")
    alpha = TradingAgent("Alpha", partner=beta)
    
    # Setup Constable with Registry
    registry = {
        "Alpha": alpha.vk_hex,
        "Beta": beta.vk_hex
    }
    constable = TreasuryConstable(registry)
    alpha.constable = constable
    
    # Scenario 1: Micro-Trade ($5,000) - Solo
    # Policy: < 10,000 needs Alpha
    alpha.attempt_trade(5000)
    
    # Scenario 2: Macro-Trade ($50,000) - Dual
    # Policy: >= 10,000 needs Alpha + Beta
    alpha.attempt_trade(50000)

    # Scenario 3: Hard Limit ($5,000,000) - Fail
    # Policy: Circuit Breaker at 1,000,000
    alpha.attempt_trade(5000000)

if __name__ == "__main__":
    run_simulation()
