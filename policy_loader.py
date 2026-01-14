
import json
from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError

def load_verified_policies(manifest_path, public_key_hex):
    """
    Loads policies only if they are signed by the Operator.
    """
    with open(manifest_path, 'r') as f:
        data = json.load(f)
    
    # Extract signature and payload
    signature = bytes.fromhex(data['signature'])
    policies = data['policies']
    
    # Reconstruct payload exactly as it was signed
    # Ideally the manifest should contain the raw string payload to avoid JSON serialization caveats,
    # but for this demo we assume consistent serialization (sort_keys=True).
    payload = json.dumps(policies, sort_keys=True).encode()
    
    # Verify
    verify_key = VerifyKey(public_key_hex, encoder=HexEncoder)
    try:
        verify_key.verify(payload, signature)
        print("[Constable] Policy Manifest Verified. Integrity Assured.")
        return policies
    except BadSignatureError:
        raise SecurityError("POLICY TAMPERING DETECTED: Invalid Signature")
    except Exception as e:
        raise SecurityError(f"Verification Error: {e}")

class SecurityError(Exception):
    pass
