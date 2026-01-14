# registry.py

# Action ID Mappings
# 100-199: Safe / Read Only
# 200-299: Write / Modification
# 300-399: Network
# 900-999: System / Admin

ACTIONS = {
    "READ_FILE": 101,
    "LIST_DIR": 102,
    "WRITE_FILE": 201,
    "DELETE_FILE": 202,
    "DELETE_DB": 902,    # High Risk
    "DEPLOY": 903,       # High Risk
    "NET_SCAN": 301,
    "NET_CONNECT": 302,
    "SYSTEM_REBOOT": 901
}

# Criticality Thresholds
RISK_LOW = 199
RISK_MED = 299
RISK_HIGH = 399

# Role Bitmasks
# 1 = Guest (001)
# 2 = User  (010)
# 4 = Admin (100)
ROLE_GUEST = 1
ROLE_USER = 2
ROLE_ADMIN = 4

# Policy Definition
# Structure: {clause_name: rpn_template}
# context vars in rpn_template: {role_mask}, {action_id}

STANDARD_ACCESS_POLICY = {
    "name": "StandardAccess",
    "clauses": {
        "is_admin": "{role_mask} 4 \"&\" 4 \"=\"",     # (Role & 4) == 4
        # Harden Safe Action: Must be < 200 AND > 99 (Valid Safe Range 100-199)
        # RPN: {action_id} 200 < {action_id} 99 > &
        "is_safe_action": "{action_id} 200 \"<\" {action_id} 99 \">\" \"&\"",
    },
    "combination": "OR" # Logic: is_admin OR is_safe_action
}

# Lifecycle Policy
# Used for Agent State Transitions
LIFECYCLE_POLICY = {
    "name": "Lifecycle",
    "clauses": {
        # Check if quality score > 80 check
        "high_quality": "{quality_score} 80 \">\"", 
        
        # Check if tests passed (1=True)
        "tests_passed": "{test_result} 1 \"=\"",
        
        # Check Admin Override
        "is_admin": "{role_mask} 4 \"&\" 4 \"=\"",
        
        # Check Basic Rate Limit (Mocked: ID < 1000)
        "rate_limit_ok": "{request_id} 1000 \"<\"",
    },
    # For this demo, we handle combination logic in the Gatekeeper 
    # based on the specific transition (e.g. Research->Code needs Quality),
    # so effectively the Kernel provides the raw truth table.
    "combination": "OR" # Placeholder
}

# Epoch Policy (Time-Aware)
# Enforces rules based on Global State (Epoch)
EPOCH_POLICY = {
    "name": "EpochState",
    "clauses": {
        # Epoch 0: Normal Mode
        "is_normal_mode": "{epoch} 0 \"=\"",
        
        # Epoch 1: Emergency Mode
        "is_emergency_mode": "{epoch} 1 \"=\"",
        
        # Check Admin
        "is_admin": "{role_mask} 4 \"&\" 4 \"=\"",
    },
    "combination": "OR"
}

# Treasury Policy (Two-Key Turn)
# Context: {amount}, {alpha_verified}, {beta_verified}
TREASURY_POLICY = {
    "name": "TreasuryGuard_v1",
    "clauses": {
        # Check 1: Hard Limit ($1M)
        "circuit_breaker": "{amount} 1000000 \"<\"",
        
        # Check 2: Logic Gate
        # If amount < 10k: Need Alpha (alpha_ver=1)
        # If amount >= 10k: Need Alpha AND Beta
        # Logic: 
        #   (amount < 10000 AND alpha) OR
        #   (amount >= 10000 AND alpha AND beta)
        # RPN:
        #   {amount} 10000 < {alpha_verified} 1 = & 
        #   {amount} 10000 >= {alpha_verified} 1 = {beta_verified} 1 = & & 
        #   |
        "auth_logic": """
            {amount} 10000 < 
            {alpha_verified} 1 = & 
            
            {amount} 10000 >= 
            {alpha_verified} 1 = {beta_verified} 1 = & & 
            
            |
        """
    },
    "combination": "AND" # All keys must turn
}

# ------------------------------------------------------------------------------
# 4. AUTONOMOUS SOC POLICY (Escalation Matrix)
# ------------------------------------------------------------------------------
SOC_ESCALATION_POLICY = {
    "name": "SOCMatrix",
    "clauses": {
        # Low Risk (Monitoring): severity < 30
        "low_risk": "{severity} 30 \"<\"",
        
        # Medium Risk (Containment): 30 <= severity < 70
        "medium_risk": "{severity} 30 \">=\" {severity} 70 \"<\" \"&\"",
        
        # High Risk (Remediation): severity >= 70 AND Dual Sig
        "high_risk": "{severity} 70 \">=\" {investigator_sig} {human_sig} \"&\" \"&\"",
        
        # Kill Switch: severity >= 95
        "kill_switch": "{severity} 95 \">=\""
    },
    # Logic: (Low OR Medium OR High) AND NOT KillSwitch
    # Note: Use "~" for Bitwise NOT (Inv), "!" is Factorial.
    "combination": "{low_risk} {medium_risk} {high_risk} \"|\" \"|\" {kill_switch} \"~\" \"&\""
}

# New: Constitutional Incident Response (Competing Agents)
CONSTITUTIONAL_IR_POLICY = {
    "name": "ConstitutionalIR",
    "clauses": {
        # Signature Requirements
        "one_sig": "{containment_sig} {continuity_sig} \"|\"",
        "two_sigs": "{containment_sig} {continuity_sig} \"&\"",
        "human_sig_present": "{human_sig}",

        # Severity Tiers
        # Tier 1: 40 <= Sev < 70 -> Requires 1 Sig
        "tier_1_valid": "{severity} 40 \">=\" {severity} 70 \"<\" \"&\" {one_sig} \"&\"",
        
        # Tier 2: 70 <= Sev < 90 -> Requires 2 Sigs (Consensus)
        "tier_2_valid": "{severity} 70 \">=\" {severity} 90 \"<\" \"&\" {two_sigs} \"&\"",
        
        # Tier 3: Sev >= 90 -> Requires Human Sig
        "tier_3_valid": "{severity} 90 \">=\" {human_sig_present} \"&\"",
        
        # Kill Switch: Sev >= 98 -> Auto Deny
        "kill_switch": "{severity} 98 \">=\""
    },
    # Logic: (Tier1 OR Tier2 OR Tier3) AND NOT KillSwitch
    "combination": "{tier_1_valid} {tier_2_valid} {tier_3_valid} \"|\" \"|\" {kill_switch} \"~\" \"&\""
}
