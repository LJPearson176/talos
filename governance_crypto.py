
import hashlib
import json
import time
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

class MerkleLogger:
    def __init__(self, filepath="audit.chain"):
        self.filepath = filepath
        self.last_hash = self._get_last_hash()

    def _get_last_hash(self):
        # Read the last line of the file to get the previous hash
        try:
            with open(self.filepath, 'r') as f:
                lines = f.readlines()
                if not lines: return "0" * 64 # Genesis Hash
                try:
                    last_entry = json.loads(lines[-1])
                    return last_entry['curr_hash']
                except json.JSONDecodeError:
                    return "0" * 64
        except FileNotFoundError:
            return "0" * 64

    def log_decision(self, agent_id, policy_name, inputs, result_bool, trace):
        # 1. Construct the Payload
        entry = {
            "prev_hash": self.last_hash,
            "ts": time.time(),
            "agent": agent_id,
            "policy": policy_name,
            "inputs": inputs,
            "decision": result_bool,
            "trace": trace
        }
        
        # 2. Compute Current Hash (The "Block ID")
        # We enforce deterministic JSON serialization for consistent hashing
        serialized = json.dumps(entry, sort_keys=True)
        curr_hash = hashlib.sha256(serialized.encode()).hexdigest()
        
        entry['curr_hash'] = curr_hash
        
        # 3. Commit to Disk
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(entry) + "\n")
            
        self.last_hash = curr_hash
        return curr_hash

class Warrant:
    def __init__(self, action, agent_id, allowed, timestamp, signature, nonce=0, expiry=0.0):
        self.action = action
        self.agent_id = agent_id
        self.allowed = allowed
        self.timestamp = timestamp
        self.signature = signature
        self.nonce = nonce
        self.expiry = expiry

    def __repr__(self):
        return f"<Warrant {self.action} allowed={self.allowed} nonce={self.nonce} exp={self.expiry} sig={self.signature[:8]}...>"

    def to_dict(self):
        return {
            "action": self.action,
            "agent_id": self.agent_id,
            "allowed": self.allowed,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "expiry": self.expiry,
            "signature": self.signature
        }

    @staticmethod
    def create(signing_key_hex, action, agent_id, allowed, timestamp, nonce=0, ttl=60):
        """Creates a signed Warrant with Expiry and Nonce."""
        sk = SigningKey(signing_key_hex, encoder=HexEncoder)
        
        expiry = timestamp + ttl
        
        # Payload to sign
        payload = json.dumps({
            "action": action,
            "agent_id": agent_id,
            "allowed": allowed,
            "timestamp": timestamp,
            "nonce": nonce,
            "expiry": expiry
        }, sort_keys=True).encode()
        
        sig = sk.sign(payload).signature.hex()
        return Warrant(action, agent_id, allowed, timestamp, sig, nonce, expiry)

    def is_valid(self, public_key_hex):
        """
        Verifies the Warrant signature AND Expiry.
        Replay protection (Nonce) must be checked by the verifier against known state.
        """
        # 1. Check Expiry
        if time.time() > self.expiry:
            return False
            
        vk = VerifyKey(public_key_hex, encoder=HexEncoder)
        
        payload = json.dumps({
            "action": self.action,
            "agent_id": self.agent_id,
            "allowed": self.allowed,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "expiry": self.expiry
        }, sort_keys=True).encode()
        
        try:
            vk.verify(payload, bytes.fromhex(self.signature))
            return True
        except:
            return False
