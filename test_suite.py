import subprocess
import sys
import os

# Ensure we are testing the latest binary
subprocess.run(["gcc", "-o", "rpn", "rpn.s"], check=True)

def run_rpn(args):
    cmd = ["./rpn"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def test(name, args, expected_output, expected_code=0):
    print(f"Testing {name: <20} ...", end=" ")
    output, code = run_rpn(args)
    
    if code != expected_code:
        print(f"FAIL (Exit Code: {code}, Expected: {expected_code})")
        print(f"  Output: {output}")
        return False
    
    if output != expected_output:
        print(f"FAIL")
        print(f"  Expected: '{expected_output}'")
        print(f"  Got:      '{output}'")
        return False
        
    print("PASS")
    return True

def main():
    print("=== RPN Calculator Comprehensive Test Suite ===\n")
    
    tests = [
        # Basic Arithmetic
        ("Add_Int", ["5", "3", "+"], "8"),
        ("Sub_Int", ["10", "4", "-"], "6"),
        ("Mul_Int", ["5", "5", "*"], "25"),
        ("Div_Int", ["20", "4", "/"], "5"),
        ("Mod_Int", ["10", "3", "%"], "1"),
        ("Pow_Int", ["2", "3", "^"], "8"),
        
        # Stack Utilities
        ("Stack_Dup", ["5", "d", "*"], "25"),
        ("Stack_Swap", ["10", "2", "s", "/"], "0"), # 2 / 10 = 0
        ("Stack_Drop", ["5", "10", "x"], "5"),
        
        # Bitwise Operations
        ("Bit_And", ["3", "5", "&"], "1"),
        ("Bit_Or", ["3", "5", "|"], "7"),
        ("Bit_Not", ["0", "~"], "-1"),
        ("Bit_LSL", ["1", "4", "l"], "16"),
        ("Bit_ASR", ["16", "2", "r"], "4"),
        
        # Logic & Comparison
        ("Log_Eq_True", ["10", "10", "="], "1"),
        ("Log_Eq_False", ["10", "5", "="], "0"),
        ("Log_Lt_True", ["5", "10", "<"], "1"),
        ("Log_Gt_True", ["10", "5", ">"], "1"),
        
        # Math Algorithms
        ("Math_GCD", ["12", "8", "g"], "4"),
        ("Math_Fact", ["5", "!"], "120"),
        
        # Input Parity (Radix-Aware atoi)
        ("In_Hex", ["0xFF"], "255"),
        ("In_Bin", ["0b101"], "5"),
        ("In_NegHex", ["-0xA"], "-10"),
        
        # Base Formatting (Output)
        ("Out_Hex", ["255", "h"], "0xFF"),
        ("Out_Bin", ["5", "b"], "0b101"),
        
        # Floating Point (Bit-Blind)
        ("Float_Add", ["2.5", "3.5", "f+", "fp"], "6.000000"),
        ("Float_Sub", ["1.5", "0.5", "f-", "fp"], "1.000000"),
        ("Float_Mul", ["2.0", "4.0", "f*", "fp"], "8.000000"),
        ("Float_Div", ["10.0", "4.0", "f/", "fp"], "2.500000"),
        ("Float_Input", ["3.14159", "fp"], "3.141590"),
        ("Float_HexBits", ["0x3FF0000000000000", "fp"], "1.000000"), # Double 1.0
        
        # Bridge Operators (Casting)
        ("Cast_Flt", ["5", "flt", "2.5", "f+", "fp"], "7.500000"),
        ("Cast_Int", ["7.9", "int"], "7"),
        
        # Hardware Transcendentals
        ("Math_Sqrt", ["9.0", "sqrt", "fp"], "3.000000"),
        ("Math_Fabs", ["-5.0", "fabs", "fp"], "5.000000"),
        ("Math_Fneg", ["10.0", "fneg", "fp"], "-10.000000"),
        ("Math_Fmin", ["1.0", "2.0", "fmin", "fp"], "1.000000"),
        ("Math_Fmax", ["1.0", "2.0", "fmax", "fp"], "2.000000"),
        
        # Error Safety
        ("Err_EmptyStack", ["+"], "Error: Invalid operation or insufficient arguments.", 1),
        ("Err_DivZero", ["10", "0", "/"], "Error: Invalid operation or insufficient arguments.", 1),
    ]
    
    passed = 0
    total = len(tests)
    
    for t in tests:
        args = t[1]
        out = t[2]
        code = t[3] if len(t) > 3 else 0
        if test(t[0], args, out, code):
            passed += 1
            
    print(f"\nSummary: {passed}/{total} Tests Passed.")
    
    if passed == total:
        print("\nSUCCESS: All calculator features verified.")
        sys.exit(0)
    else:
        print("\nFAILURE: Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
