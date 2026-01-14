
import json
import time
from governance import DAEMON, Policy
from governance_crypto import MerkleLogger, Warrant
from policy_loader import load_verified_policies

class CryptoGovernance:
    def __init__(self, manifest_path="policies.json", keys_path="keys.json"):
        # 1. Load Keys
        try:
            with open(keys_path) as f:
                keys = json.load(f)
                self.root_pub = keys['root']['public']
                self.constable_priv = keys['constable']['private']
                self.constable_pub = keys['constable']['public']
        except FileNotFoundError:
            raise RuntimeError("keys.json not found. Run keygen.py first.")

        # 2. Secure Boot: Load Verified Policies
        print("[CryptoGov] Booting... Verifying Policy Manifest...")
        self.policies_def = load_verified_policies(manifest_path, self.root_pub)
        self.policies = {name: Policy(defn) for name, defn in self.policies_def.items()}
        print(f"[CryptoGov] Loaded {len(self.policies)} Verified Policies.")
        
        # 3. Init Merkle Logger
        self.logger = MerkleLogger("audit.chain")
        
    def verify_action(self, agent_id, action, role_mask, context_overrides=None):
        """
        Verifies an action and returns a signed Warrant (or None/Denied Warrant).
        """
        # 1. Select Policy
        # For demo, we default to StandardAccess unless EPOCH is set
        policy_name = "StandardAccess"
        
        # Merge context
        context = {
            "role_mask": str(role_mask),
            "action_id": str(action_map(action))
        }
        if context_overrides:
            context.update({k: str(v) for k, v in context_overrides.items()})
            if "epoch" in context:
                # Simple logic: If epoch > 0, use EpochGov
                if int(context["epoch"]) > 0:
                    policy_name = "EpochGov"

        if policy_name not in self.policies:
            print(f"[CryptoGov] Policy {policy_name} not found.")
            return self._deny(agent_id, action, "PolicyNotFound")

        policy = self.policies[policy_name]
        
        # 2. Execute Kernel (Zero-Knowledge Logic)
        # The Policy object uses the GLOBAL DAEMON (rpn.s)
        proof = policy.evaluate(context)
        
        # 3. Log to Merkle Chain (Attestation)
        block_hash = self.logger.log_decision(
            agent_id=agent_id,
            policy_name=policy_name,
            inputs=context,
            result_bool=proof.allowed,
            trace=proof.trace
        )
        
        print(f"[CryptoGov] Decision Logged. Block Hash: {block_hash[:16]}...")

        # 4. Issue Warrant
        if proof.allowed:
            warrant = Warrant.create(
                self.constable_priv,
                action,
                agent_id,
                allowed=True,
                timestamp=time.time()
            )
            return warrant
        else:
            # Return a Denied Warrant (Proof of Rejection)
            # Useful for reasoning loops
            return Warrant.create(
                self.constable_priv,
                action,
                agent_id,
                allowed=False,
                timestamp=time.time()
            )

    def _deny(self, agent_id, action, reason):
        return Warrant.create(self.constable_priv, action, agent_id, False, time.time())

# Helper to map action strings to IDs (Duplicate from registry logic for now)
def action_map(action_name):
    from registry import ACTIONS
    return ACTIONS.get(action_name, 0)
