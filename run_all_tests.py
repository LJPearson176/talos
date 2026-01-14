
import unittest
import sys
import subprocess

def run_tests():
    print("==========================================")
    print("      CONSTABLE GOVERNANCE TEST SUITE     ")
    print("==========================================\n")
    
    # 1. Kernel Regression (test_suite.py)
    print(">>> Running Kernel Regression (rpn.s)...")
    try:
        # Run test_suite.py as subprocess since it uses sys.exit
        subprocess.run([sys.executable, "test_suite.py"], check=True)
    except subprocess.CalledProcessError:
        print("!!! Kernel Regression FAILED")
        sys.exit(1)
    print("\n")
        
    # 2. Middleware Units (test_governance.py)
    print(">>> Running Governance Middleware Tests...")
    # Load tests dynamically
    suite_gov = unittest.defaultTestLoader.discover('.', pattern='test_governance.py')
    result_gov = unittest.TextTestRunner(verbosity=1).run(suite_gov)
    if not result_gov.wasSuccessful():
        print("!!! Governance Tests FAILED")
        sys.exit(1)
    print("\n")
        
    # 3. System Integration (test_integration.py)
    print(">>> Running System Integration Tests...")
    suite_int = unittest.defaultTestLoader.discover('.', pattern='test_integration.py')
    result_int = unittest.TextTestRunner(verbosity=1).run(suite_int)
    if not result_int.wasSuccessful():
        print("!!! Integration Tests FAILED")
        sys.exit(1)
        
    print("\n==========================================")
    print("      ALL SYSTEMS VERIFIED: GO.")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
