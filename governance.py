
import subprocess
import os
import time
from registry import ACTIONS, STANDARD_ACCESS_POLICY

class DecisionProof:
    def __init__(self, allowed, trace, policy_name):
        self.allowed = allowed
        self.trace = trace
        self.policy_name = policy_name
        self.timestamp = time.time()

    def __repr__(self):
        return f"<DecisionProof allowed={self.allowed} policy={self.policy_name} trace={self.trace}>"

    def to_dict(self):
        return {
            "allowed": self.allowed,
            "policy": self.policy_name,
            "trace": self.trace,
            "timestamp": self.timestamp
        }

# --- Daemon Controller ---

RPN_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpn")

class DaemonController:
    def __init__(self):
        self.process = None
        self._start()

    def _start(self):
        """Starts the RPN daemon process."""
        print(f"[Daemon] Starting RPN kernel at {RPN_BIN}")
        try:
            self.process = subprocess.Popen(
                [RPN_BIN],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,      # Binary Mode
                bufsize=0        # Unbuffered
            )
        except Exception as e:
            print(f"[Daemon] Failed to start: {e}")
            self.process = None

    def evaluate(self, expr_tokens):
        """
        Sends a space-separated expression to the daemon using TLV Framing.
        Header: 4 Bytes Length (BigEndian) + 1 Byte Type (1=Exec)
        """
        if not self.process or self.process.poll() is not None:
            print("[Daemon] Process dead, restarting...")
            self._start()
            if not self.process:
                return "0"

        # Construct Body
        input_str = " ".join(expr_tokens)
        body = input_str.encode('utf-8')
        
        # Construct Header
        # Length = len(body)
        # Type = 1 (Command)
        import struct
        header = struct.pack('>IB', len(body), 1)
        
        packet = header + body
        
        try:
            self.process.stdin.write(packet)
            self.process.stdin.flush()
            
            # Read response (Still line-based for now as per plan, or text output)
            # The kernel prints formatted content. Since we turned off text=True,
            # we read bytes and decode.
            output_bytes = self.process.stdout.readline()
            return output_bytes.decode('utf-8').strip()
            
        except BrokenPipeError:
            print("[Daemon] Broken Pipe. Restarting.")
            self._start()
            return "0"
        except Exception as e:
            print(f"[Daemon] Logic Error: {e}")
            return "0"

    def shutdown(self):
        if self.process:
            self.process.terminate()

# Global Daemon
DAEMON = DaemonController()

class Policy:
    def __init__(self, policy_def):
        self.name = policy_def["name"]
        self.clauses = policy_def["clauses"]
        self.combination = policy_def["combination"]

    def evaluate(self, context):
        """
        Evaluates the policy against the given context.
        Returns a DecisionProof object.
        """
        trace = {}
        
        # 1. Evaluate each clause independently
        for clause_name, template in self.clauses.items():
            # Substitute context variables
            # We assume template strings are safe since they come from trusted registry
            try:
                rpn_expr = template.format(**context)
                result_bool = self._run_kernel(rpn_expr)
                trace[clause_name] = result_bool
                
                # Feedback Loop: Allow subsequent clauses to use this result
                context[clause_name] = "1" if result_bool else "0"
            except Exception as e:
                print(f"[Policy] Error evaluating clause '{clause_name}': {e}")
                trace[clause_name] = False # Fail Closed
                context[clause_name] = "0"

        # 2. Combine results
        # Current logic is simple OR or AND. 
        # Ideally this would also be an RPN expression, but for now we follow the spec.
        if self.combination == "OR":
            final_result = any(trace.values())
        elif self.combination == "AND":
            final_result = all(trace.values())
        else:
            # RPN Combination Logic
            # Map trace booleans to "1"/"0"
            trace_map = {k: ("1" if v else "0") for k, v in trace.items()}
            try:
                combined_expr = self.combination.format(**trace_map)
                final_result = self._run_kernel(combined_expr)
            except Exception as e:
                print(f"[Policy] Error evaluating combination logic: {e}")
                final_result = False

        return DecisionProof(final_result, trace, self.name)

    def _run_kernel(self, rpn_expr):
        """
        Executes a single RPN expression against the persistent kernel daemon.
        """
        
        # Parse tokens and strip quotes (Legacy compatibility)
        raw_tokens = rpn_expr.split()
        args = []
        for token in raw_tokens:
            if (token.startswith('"') and token.endswith('"')) or \
               (token.startswith("'") and token.endswith("'")):
                args.append(token[1:-1])
            else:
                args.append(token)

        # Send to Daemon
        output = DAEMON.evaluate(args)
        
        return output == "1"

# Global Instance
_current_policy = Policy(STANDARD_ACCESS_POLICY)

def verify_action(role_mask, action_name, param_val=0, context_overrides=None):
    """
    Verifies an action and returns a DecisionProof object.
    
    Args:
        role_mask (int): User role bitmask.
        action_name (str): Action string (e.g. "READ_FILE").
        param_val (int): Optional parameter.
        context_overrides (dict): Optional extra context variables (e.g. "epoch", "tick").
        
    Returns:
        DecisionProof: object containing boolean result and trace.
    """
    
    # 1. Encode Action
    if action_name not in ACTIONS:
        # Unknown action -> Deny with empty trace
        return DecisionProof(False, {"unknown_action": False}, "Unknown")
        
    action_id = ACTIONS[action_name]
    
    # 2. Build Context
    context = {
        "role_mask": str(role_mask),
        "action_id": str(action_id)
    }
    
    # 3. Inject Overrides (State Injection)
    if context_overrides:
        for k, v in context_overrides.items():
            context[k] = str(v)
            
    # 4. Evaluate Policy
    # Note: In a real system, we might switch policies based on context (e.g. use EPOCH_POLICY).
    # For now, we rely on the caller setting the global policy or just using the current one.
    # To support the demo, we should allow switching the policy instance or have the caller use a different method.
    # But to keep it simple, let's keep _current_policy global, OR allow passing policy?
    
    # Actually, for the demo "Time-Aware", we want to use EPOCH_POLICY.
    # But verify_action uses _current_policy (which is StandardAccess).
    # Let's add a helper to switch or pass policy?
    # Or better: Just use the set_policy helper if we had one.
    # Let's add a simple way to use a specific policy or modify _current_policy.
    
    proof = _current_policy.evaluate(context)
    
    # 5. Ledger (The Court Reporter)
    _log_to_ledger(proof, context)
    
    return proof
    
def set_active_policy(policy_def):
    global _current_policy
    _current_policy = Policy(policy_def)

def _log_to_ledger(proof, context):
    """
    Appends the decision proof to an immutable jsonl log.
    In a real system, this would write to a secure audit trail.
    """
    import json
    import time
    
    entry = {
        "timestamp": time.time(),
        "policy": proof.policy_name,
        "allowed": proof.allowed,
        "trace": proof.trace,
        "context": context
    }
    
    try:
        with open("audit_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[Ledger] Error writing to log: {e}")
