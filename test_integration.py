
import unittest
import io
import sys
from contextlib import redirect_stdout
from governed_graph import TimeSimulation

class TestIntegration(unittest.TestCase):
    
    def test_governed_simulation(self):
        """
        Runs the full `governed_graph.py` simulation and asserts on the output log.
        This ensures the entire system (Gatekeeper -> Governance -> RPN) works in concert.
        """
        
        # Capture stdout
        f = io.StringIO()
        with redirect_stdout(f):
            sim = TimeSimulation()
            sim.run()
            
        output = f.getvalue()
        
        # Assertions
        
        # 1. Check Normal Mode Approval
        # "[>] APPROVED. (Normal=True, Emergency=False, Admin=False)"
        self.assertIn("[>] APPROVED. (Normal=True, Emergency=False, Admin=False)", output)
        
        # 2. Check Emergency Mode Denial (Guest)
        # "[x] DENIED.   (Normal=False, Emergency=True, Admin=False)"
        self.assertIn("[x] DENIED.   (Normal=False, Emergency=True, Admin=False)", output)
        
        # 3. Check Emergency Mode Approval (Admin)
        # "[>] APPROVED. (Normal=False, Emergency=True, Admin=True)"
        self.assertIn("[>] APPROVED. (Normal=False, Emergency=True, Admin=True)", output)
        
        print("\n[Integration] Full System Simulation Verified.")

if __name__ == "__main__":
    unittest.main()
