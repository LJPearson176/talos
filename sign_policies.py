
import json
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
from registry import STANDARD_ACCESS_POLICY, EPOCH_POLICY, LIFECYCLE_POLICY, TREASURY_POLICY, SOC_ESCALATION_POLICY, CONSTITUTIONAL_IR_POLICY

# Aggregate policies
POLICIES = {
    "StandardAccess": STANDARD_ACCESS_POLICY,
    "EpochGov": EPOCH_POLICY,
    "Lifecycle": LIFECYCLE_POLICY,
    "TreasuryGuard_v1": TREASURY_POLICY,
    "SOCMatrix": SOC_ESCALATION_POLICY,
    "ConstitutionalIR": CONSTITUTIONAL_IR_POLICY
}

def sign_manifest():
    # Load Root Key
    with open("keys.json", "r") as f:
        keys = json.load(f)
        root_priv = keys["root"]["private"]
        
    sk = SigningKey(root_priv, encoder=HexEncoder)
    
    # Serialize Policies
    payload = json.dumps(POLICIES, sort_keys=True).encode()
    
    # Sign
    sig = sk.sign(payload).signature.hex()
    
    # Create Manifest
    manifest = {
        "signature": sig,
        "policies": POLICIES
    }
    
    with open("policies.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[Manifest] Signed policies.json with Root Key: {keys['root']['public']}")

if __name__ == "__main__":
    sign_manifest()
