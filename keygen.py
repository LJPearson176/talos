
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
import json
import os

def generate_keys():
    # 1. Root Key (For signing Manifests)
    root_sk = SigningKey.generate()
    root_vk = root_sk.verify_key
    
    # 2. Constable Key (For signing Warrants/Attestations)
    constable_sk = SigningKey.generate()
    constable_vk = constable_sk.verify_key
    
    keys = {
        "root": {
            "private": root_sk.encode(encoder=HexEncoder).decode('utf-8'),
            "public": root_vk.encode(encoder=HexEncoder).decode('utf-8')
        },
        "constable": {
            "private": constable_sk.encode(encoder=HexEncoder).decode('utf-8'),
            "public": constable_vk.encode(encoder=HexEncoder).decode('utf-8')
        }
    }
    
    with open("keys.json", "w") as f:
        json.dump(keys, f, indent=2)
        
    print("[KeyGen] Generated keys.json")
    print(f"Root Public: {keys['root']['public']}")
    print(f"Constable Public: {keys['constable']['public']}")

if __name__ == "__main__":
    generate_keys()
