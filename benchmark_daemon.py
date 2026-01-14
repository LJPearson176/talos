
import time
from governance import verify_action, set_active_policy
from registry import STANDARD_ACCESS_POLICY, ROLE_ADMIN, ROLE_GUEST

def run_benchmark():
    print("=== Daemon Mode Benchmark ===")
    
    # Setup
    set_active_policy(STANDARD_ACCESS_POLICY)
    
    # Warmup
    verify_action(ROLE_ADMIN, "SYSTEM_REBOOT")
    
    iterations = 1000
    start_time = time.time()
    
    print(f"Running {iterations} checks...")
    for _ in range(iterations):
        # Mix of allowed/denied to exercise logic
        verify_action(ROLE_ADMIN, "SYSTEM_REBOOT")
        verify_action(ROLE_GUEST, "SYSTEM_REBOOT")
        
    end_time = time.time()
    total_time = end_time - start_time
    avg_fe_latency = (total_time / iterations) * 1000  # ms
    
    print(f"Total Time: {total_time:.4f}s")
    print(f"Avg Latency: {avg_fe_latency:.4f}ms per check")
    
    if avg_fe_latency < 1.0:
        print("PASS: Latency < 1ms")
    else:
        print("WARN: Latency > 1ms (Still faster than 30ms fork)")

if __name__ == "__main__":
    run_benchmark()
