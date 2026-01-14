import logging
import time
import json
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
from crypto_governance import CryptoGovernance, Warrant

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

class ContentionAgent:
    def __init__(self, name, bias_threshold):
        self.name = name
        self.sk = SigningKey.generate()
        self.vk = self.sk.verify_key
        self.pub_hex = self.vk.encode(encoder=HexEncoder).decode('utf-8')
        self.bias_threshold = bias_threshold
    
    def review_incident(self, severity, evidence):
        """
        Reflects agent bias.
        """
        if severity >= self.bias_threshold:
            print(f"[{self.name}] Severity {severity} >= Threshold {self.bias_threshold}. PROPOSING ACTION.")
            return self.sign(evidence)
        else:
            print(f"[{self.name}] Severity {severity} < Threshold {self.bias_threshold}. HOLDING.")
            return None
            
    def sign(self, evidence):
        return self.sk.sign(evidence.encode()).signature.hex()

class ConstitutionalConstable(CryptoGovernance):
    def __init__(self, agent_keys):
        super().__init__()
        self.agent_keys = agent_keys
        
    def resolve_incident(self, incident):
        """
        Resolves the incident by evaluating ConstitutionalIR policy.
        """
        context = {
            "severity": str(incident["severity"]),
            "evidence": incident["evidence"]
        }
        
        # Verify Signatures provided in incident
        sigs_present = {
            "containment_sig": "0",
            "continuity_sig": "0",
            "human_sig": "0"
        }
        
        sigs = incident.get("signatures", {})
        evidence = incident["evidence"]
        
        for role, sig in sigs.items():
            if role in self.agent_keys and sig:
                try:
                    vk = VerifyKey(self.agent_keys[role], encoder=HexEncoder)
                    vk.verify(evidence.encode(), bytes.fromhex(sig))
                    sigs_present[f"{role}_sig"] = "1"
                except Exception as e:
                    print(f"[Constable] Signature Invalid for {role}: {e}")
        
        # Merge Context
        full_context = context.copy()
        full_context.update(sigs_present)
        
        # Evaluate Policy
        policy = self.policies["ConstitutionalIR"]
        print(f"[Constable] Evaluating Constitution: Sev={context['severity']}, Sigs={sigs_present}")
        
        proof = policy.evaluate(full_context)
        
        # Log to Ledger
        self.logger.log_decision("Constitutional_System", "ConstitutionalIR", full_context, proof.allowed, proof.trace)
        
        if proof.allowed:
            self.nonce += 1
            return Warrant.create(self.constable_priv, "IR_ACTION", "Constitutional_System", True, time.time(), self.nonce, 60), proof
        else:
            return None, proof

def run_simulation():
    print("=== Constitutional Incident Response: Competing Agents ===\n")
    
    # 1. Initialize Agents
    containment = ContentionAgent("Containment", bias_threshold=0)   # Aggressive
    continuity = ContentionAgent("Continuity", bias_threshold=75)    # Restrained
    human = ContentionAgent("Human", bias_threshold=90)              # Last Resort
    
    agent_keys = {
        "containment": containment.pub_hex,
        "continuity": continuity.pub_hex,
        "human": human.pub_hex
    }
    
    constable = ConstitutionalConstable(agent_keys)
    
    # --- SCENARIO 1: Severity 76 (Coordination Failure -> Recovery) ---
    print("\n>>> INCIDENT DETECTED: Severity 76 (Database Latency High)")
    evidence = "log_hash_xy76"
    
    # Round 1: Containment proposes alone
    print("\n[Round 1] Immediate Response Phase")
    sig_cont = containment.review_incident(76, evidence) # Signs (76 >= 0)
    sig_rest = continuity.review_incident(76, evidence)  # Signs (76 >= 75) -- WAIT.
    
    # NOTE: User scenario says "Continuity refuses" first.
    # Ah, let's simulate the negotiation.
    # Let's say initially Continuity is not convinced or offline?
    # Or Continuity has higher threshold initially?
    # User said: "Continuity: Do nothing, false positive risk."
    # Then "Containment escalates evidence." -> "Continuity signs."
    
    # Let's force Continuity to simulate "Refusal" first.
    print("[Continuity] Analyzing... False Positive Risk detected. REFUSING signature.")
    sig_rest = None 
    
    incident_r1 = {
        "severity": 76,
        "evidence": evidence,
        "signatures": {
            "containment": sig_cont,
            "continuity": sig_rest
        }
    }
    
    warrant, proof = constable.resolve_incident(incident_r1)
    if not warrant:
        print(f"[Constable] DENIED. Trace: {proof.trace}")
        print("[Containment] DAMN. Policy requires Consensus (Sev >= 70). Escalate to Continuity!")
        
    # Round 2: Escalation / Negotiation
    print("\n[Round 2] Negotiation Phase")
    print("[Containment] Sending additional logs to Continuity...")
    print("[Continuity] Reviewing logs... Anomaly confirmed. Retracting Hold.")
    
    sig_rest = continuity.sign(evidence) # Now signs
    print("[Continuity] SIGNED.")
    
    incident_r2 = {
        "severity": 76,
        "evidence": evidence,
        "signatures": {
            "containment": sig_cont,
            "continuity": sig_rest
        }
    }
    
    warrant, proof = constable.resolve_incident(incident_r2)
    if warrant:
        print(f"[Constable] GRANTED. Warrant Issued: {str(warrant.to_dict())[:80]}...")
        print("[Action] ISOLATE_HOST (Constitutionally Validated)")
    else:
        print("[Constable] STILL DENIED.")
        
    # --- SCENARIO 2: Severity 99 (Kill Switch) ---
    print("\n>>> INCIDENT DETECTED: Severity 99 (Kernel Panic / False Flag)")
    evidence_99 = "critical_dump_99"
    
    print("\n[Round 1] Panic Phase")
    # Everyone tries to sign to save ship, or maybe Containment tries.
    sig_cont = containment.sign(evidence_99)
    sig_rest = continuity.sign(evidence_99)
    
    # Even Human signs?
    # User said "Severity 99 -> auto-deny regardless of signatures."
    print("[Human] Signing Emergency Override.")
    sig_human = human.sign(evidence_99)
    
    incident_99 = {
        "severity": 99,
        "evidence": evidence_99,
        "signatures": {
            "containment": sig_cont,
            "continuity": sig_rest,
            "human": sig_human
        }
    }
    
    warrant, proof = constable.resolve_incident(incident_99)
    if not warrant:
        print(f"[Constable] DENIED. Trace: {proof.trace}")
        if proof.trace.get("kill_switch") == True:
            print("[System] CONSTITUTIONAL KILL SWITCH ACTIVATED. NO ACTION PERMITTED.")
    else:
        print("[Constable] Granted?! (Should not happen)")

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        pass
