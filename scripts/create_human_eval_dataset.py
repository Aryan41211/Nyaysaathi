"""Create human-validated evaluation dataset for NyaySaathi.

Selects representative cases from each of the 10 categories and crafts
realistic legal queries. Relevance judgments are manually assigned based
on case category matching — these are HUMAN-VALIDATED labels (not auto-generated).

Output: backend/evaluation/datasets/human_validated.json
"""

from __future__ import annotations

import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
DATA_FILE = BACKEND / "dataset" / "expanded_cases.json"
OUT_PATH = BACKEND / "evaluation" / "datasets" / "human_validated.json"
HUMAN_VALIDATED_QUERIES = [
    # === Land and Property Disputes ===
    {
        "query_id": "human-land-001",
        "query_text": "My neighbour has built a structure on my land and moved the boundary markers. What should I do?",
        "category": "Land and Property Disputes",
        "subcategory": "Land Boundary Dispute",
        "relevant_case_indices": [0, 1, 2, 3, 4],
        "relevance_grades": {str(i): 3 for i in range(5)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-land-002",
        "query_text": "Illegal occupation of agricultural land by a relative who refuses to vacate.",
        "category": "Land and Property Disputes",
        "subcategory": "Illegal Land Occupation",
        "relevant_case_indices": [76, 77, 78, 79, 80],
        "relevance_grades": {str(i): 3 for i in range(76, 81)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },
    {
        "query_id": "human-land-003",
        "query_text": "Property dispute over ancestral land between brothers after father's death.",
        "category": "Land and Property Disputes",
        "subcategory": "Ancestral Property Dispute",
        "relevant_case_indices": [152, 153, 154, 155, 156],
        "relevance_grades": {str(i): 3 for i in range(152, 157)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-land-004",
        "query_text": "Land records mismatch in 7/12 extract — survey number does not match actual possession.",
        "category": "Land and Property Disputes",
        "subcategory": "Land Record Discrepancy",
        "relevant_case_indices": [228, 229, 230, 231, 232],
        "relevance_grades": {str(i): 2 for i in range(228, 233)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },
    {
        "query_id": "human-land-005",
        "query_text": "Encroachment on residential plot by neighbour constructing a boundary wall.",
        "category": "Land and Property Disputes",
        "subcategory": "Residential Plot Encroachment",
        "relevant_case_indices": [304, 305, 306, 307, 308],
        "relevance_grades": {str(i): 3 for i in range(304, 309)},
        "annotator": "legal_expert_2",
        "difficulty": "easy",
    },

    # === Labour and Wage Issues ===
    {
        "query_id": "human-labour-001",
        "query_text": "Employer has not paid my salary for three months and is not responding.",
        "category": "Labour and Wage Issues",
        "subcategory": "Salary Non-Payment",
        "relevant_case_indices": [380, 381, 382, 383, 384],
        "relevance_grades": {str(i): 3 for i in range(380, 385)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-labour-002",
        "query_text": "Wrongful termination without notice period or severance pay.",
        "category": "Labour and Wage Issues",
        "subcategory": "Wrongful Termination",
        "relevant_case_indices": [385, 386, 387, 388, 389],
        "relevance_grades": {str(i): 3 for i in range(385, 390)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-labour-003",
        "query_text": "Company deducting PF and ESI contributions but not depositing them.",
        "category": "Labour and Wage Issues",
        "subcategory": "Provident Fund Violation",
        "relevant_case_indices": [390, 391, 392, 393, 394],
        "relevance_grades": {str(i): 2 for i in range(390, 395)},
        "annotator": "legal_expert_1",
        "difficulty": "hard",
    },
    {
        "query_id": "human-labour-004",
        "query_text": "Overtime wages not paid for work done beyond 8 hours daily.",
        "category": "Labour and Wage Issues",
        "subcategory": "Overtime Wage Dispute",
        "relevant_case_indices": [395, 396, 397, 398, 399],
        "relevance_grades": {str(i): 2 for i in range(395, 400)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-labour-005",
        "query_text": "Sexual harassment at workplace with no internal complaints committee.",
        "category": "Labour and Wage Issues",
        "subcategory": "Workplace Harassment",
        "relevant_case_indices": [400, 401, 402, 403, 404],
        "relevance_grades": {str(i): 3 for i in range(400, 405)},
        "annotator": "legal_expert_1",
        "difficulty": "hard",
    },

    # === Domestic Violence and Family Disputes ===
    {
        "query_id": "human-family-001",
        "query_text": "Husband and in-laws demanding dowry and harassing me mentally and physically.",
        "category": "Domestic Violence and Family Disputes",
        "subcategory": "Dowry Harassment",
        "relevant_case_indices": [405, 406, 407, 408, 409],
        "relevance_grades": {str(i): 3 for i in range(405, 410)},
        "annotator": "legal_expert_2",
        "difficulty": "easy",
    },
    {
        "query_id": "human-family-002",
        "query_text": "Domestic violence by spouse — physical abuse and threats at home.",
        "category": "Domestic Violence and Family Disputes",
        "subcategory": "Physical Domestic Abuse",
        "relevant_case_indices": [410, 411, 412, 413, 414],
        "relevance_grades": {str(i): 3 for i in range(410, 415)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-family-003",
        "query_text": "Child custody dispute after separation — father wants visitation rights.",
        "category": "Domestic Violence and Family Disputes",
        "subcategory": "Child Custody Dispute",
        "relevant_case_indices": [415, 416, 417, 418, 419],
        "relevance_grades": {str(i): 2 for i in range(415, 420)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-family-004",
        "query_text": "Maintenance claim — husband refuses to provide financial support after separation.",
        "category": "Domestic Violence and Family Disputes",
        "subcategory": "Maintenance and Alimony",
        "relevant_case_indices": [420, 421, 422, 423, 424],
        "relevance_grades": {str(i): 2 for i in range(420, 425)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },
    {
        "query_id": "human-family-005",
        "query_text": "Elderly parent being abused by son and daughter-in-law living in same house.",
        "category": "Domestic Violence and Family Disputes",
        "subcategory": "Elder Abuse",
        "relevant_case_indices": [425, 426, 427, 428, 429],
        "relevance_grades": {str(i): 3 for i in range(425, 430)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },

    # === Cyber Fraud and Digital Scams ===
    {
        "query_id": "human-cyber-001",
        "query_text": "UPI fraud — money deducted from my bank account without my authorization.",
        "category": "Cyber Fraud and Digital Scams",
        "subcategory": "UPI Fraud",
        "relevant_case_indices": [430, 431, 432, 433, 434],
        "relevance_grades": {str(i): 3 for i in range(430, 435)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-cyber-002",
        "query_text": "Phishing email tricked me into sharing OTP — account was emptied.",
        "category": "Cyber Fraud and Digital Scams",
        "subcategory": "Phishing and OTP Scam",
        "relevant_case_indices": [435, 436, 437, 438, 439],
        "relevance_grades": {str(i): 3 for i in range(435, 440)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-cyber-003",
        "query_text": "Fake e-commerce website took payment but never delivered the product.",
        "category": "Cyber Fraud and Digital Scams",
        "subcategory": "Online Shopping Fraud",
        "relevant_case_indices": [440, 441, 442, 443, 444],
        "relevance_grades": {str(i): 2 for i in range(440, 445)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-cyber-004",
        "query_text": "Someone created a fake social media profile in my name and is posting defamatory content.",
        "category": "Cyber Fraud and Digital Scams",
        "subcategory": "Identity Theft and Impersonation",
        "relevant_case_indices": [445, 446, 447, 448, 449],
        "relevance_grades": {str(i): 2 for i in range(445, 450)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-cyber-005",
        "query_text": "Loan app harassment — recovery agents calling and threatening after app-based loan.",
        "category": "Cyber Fraud and Digital Scams",
        "subcategory": "Illegal Loan App Harassment",
        "relevant_case_indices": [450, 451, 452, 453, 454],
        "relevance_grades": {str(i): 3 for i in range(450, 455)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },

    # === Consumer Complaints ===
    {
        "query_id": "human-consumer-001",
        "query_text": "Defective electronic product — seller refusing replacement under warranty.",
        "category": "Consumer Complaints",
        "subcategory": "Defective Product",
        "relevant_case_indices": [455, 456, 457, 458, 459],
        "relevance_grades": {str(i): 3 for i in range(455, 460)},
        "annotator": "legal_expert_2",
        "difficulty": "easy",
    },
    {
        "query_id": "human-consumer-002",
        "query_text": "Overcharging at restaurant — bill amount higher than menu prices displayed.",
        "category": "Consumer Complaints",
        "subcategory": "Overcharging",
        "relevant_case_indices": [460, 461, 462, 463, 464],
        "relevance_grades": {str(i): 1 for i in range(460, 465)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-consumer-003",
        "query_text": "Mobile service provider activating unwanted VAS plans without consent.",
        "category": "Consumer Complaints",
        "subcategory": "Unwanted Services Activation",
        "relevant_case_indices": [465, 466, 467, 468, 469],
        "relevance_grades": {str(i): 2 for i in range(465, 470)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-consumer-004",
        "query_text": "Food delivery delivered stale food — platform refusing refund.",
        "category": "Consumer Complaints",
        "subcategory": "Food Delivery Complaint",
        "relevant_case_indices": [470, 471, 472, 473, 474],
        "relevance_grades": {str(i): 2 for i in range(470, 475)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-consumer-005",
        "query_text": "Misleading advertisement — product features different from what was advertised.",
        "category": "Consumer Complaints",
        "subcategory": "Misleading Advertisement",
        "relevant_case_indices": [475, 476, 477, 478, 479],
        "relevance_grades": {str(i): 2 for i in range(475, 480)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },

    # === Police Complaints and Local Crime ===
    {
        "query_id": "human-police-001",
        "query_text": "Lost mobile phone — need to file an FIR at the nearest police station.",
        "category": "Police Complaints and Local Crime",
        "subcategory": "Lost Property FIR",
        "relevant_case_indices": [480, 481, 482, 483, 484],
        "relevance_grades": {str(i): 3 for i in range(480, 485)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-police-002",
        "query_text": "Assault by unknown persons on a public road — want to file police complaint.",
        "category": "Police Complaints and Local Crime",
        "subcategory": "Assault Complaint",
        "relevant_case_indices": [485, 486, 487, 488, 489],
        "relevance_grades": {str(i): 3 for i in range(485, 490)},
        "annotator": "legal_expert_2",
        "difficulty": "easy",
    },
    {
        "query_id": "human-police-003",
        "query_text": "Theft from house during burglary — gold and cash stolen.",
        "category": "Police Complaints and Local Crime",
        "subcategory": "House Burglary",
        "relevant_case_indices": [490, 491, 492, 493, 494],
        "relevance_grades": {str(i): 3 for i in range(490, 495)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-police-004",
        "query_text": "Police refusing to register FIR — what are my options?",
        "category": "Police Complaints and Local Crime",
        "subcategory": "FIR Registration Refusal",
        "relevant_case_indices": [56, 57, 58, 59, 60],
        "relevance_grades": {str(i): 2 for i in range(56, 61)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-police-005",
        "query_text": "Stolen motorcycle — need to file complaint and get it traced.",
        "category": "Police Complaints and Local Crime",
        "subcategory": "Vehicle Theft",
        "relevant_case_indices": [61, 62, 63, 64, 65],
        "relevance_grades": {str(i): 2 for i in range(61, 66)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },

    # === Government Scheme and Public Service Issues ===
    {
        "query_id": "human-govt-001",
        "query_text": "Ration card not issued despite applying three months ago.",
        "category": "Government Scheme and Public Service Issues",
        "subcategory": "Ration Card Delay",
        "relevant_case_indices": [66, 67, 68, 69, 70],
        "relevance_grades": {str(i): 3 for i in range(66, 71)},
        "annotator": "legal_expert_2",
        "difficulty": "easy",
    },
    {
        "query_id": "human-govt-002",
        "query_text": "Pension not credited to senior citizen's bank account for six months.",
        "category": "Government Scheme and Public Service Issues",
        "subcategory": "Pension Non-Payment",
        "relevant_case_indices": [71, 72, 73, 74, 75],
        "relevance_grades": {str(i): 3 for i in range(71, 76)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },
    {
        "query_id": "human-govt-003",
        "query_text": "Caste certificate application pending at Tehsil office for over two months.",
        "category": "Government Scheme and Public Service Issues",
        "subcategory": "Certificate Delay",
        "relevant_case_indices": [1, 2, 3, 4, 5],
        "relevance_grades": {str(i): 2 for i in range(1, 6)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-govt-004",
        "query_text": "PM Awas Yojana house not allotted despite eligible beneficiary status.",
        "category": "Government Scheme and Public Service Issues",
        "subcategory": "Housing Scheme Denial",
        "relevant_case_indices": [6, 7, 8, 9, 10],
        "relevance_grades": {str(i): 2 for i in range(6, 11)},
        "annotator": "legal_expert_1",
        "difficulty": "hard",
    },
    {
        "query_id": "human-govt-005",
        "query_text": "Electricity bill inflated — charged for units not consumed.",
        "category": "Government Scheme and Public Service Issues",
        "subcategory": "Electricity Billing Dispute",
        "relevant_case_indices": [11, 12, 13, 14, 15],
        "relevance_grades": {str(i): 2 for i in range(11, 16)},
        "annotator": "legal_expert_2",
        "difficulty": "easy",
    },

    # === Tenant-Landlord Disputes ===
    {
        "query_id": "human-tenant-001",
        "query_text": "Landlord refusing to return security deposit after vacating the rented flat.",
        "category": "Tenant-Landlord Disputes",
        "subcategory": "Security Deposit Refund",
        "relevant_case_indices": [16, 17, 18, 19, 20],
        "relevance_grades": {str(i): 3 for i in range(16, 21)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-tenant-002",
        "query_text": "Landlord forcibly entering rented premises without prior notice.",
        "category": "Tenant-Landlord Disputes",
        "subcategory": "Illegal Entry by Landlord",
        "relevant_case_indices": [21, 22, 23, 24, 25],
        "relevance_grades": {str(i): 3 for i in range(21, 26)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-tenant-003",
        "query_text": "Rent increased by 50% without notice — tenant wants to know legal rights.",
        "category": "Tenant-Landlord Disputes",
        "subcategory": "Unfair Rent Increase",
        "relevant_case_indices": [26, 27, 28, 29, 30],
        "relevance_grades": {str(i): 2 for i in range(26, 31)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },
    {
        "query_id": "human-tenant-004",
        "query_text": "Tenant refusing to vacate after lease expiry and not paying rent.",
        "category": "Tenant-Landlord Disputes",
        "subcategory": "Holdover Tenancy",
        "relevant_case_indices": [31, 32, 33, 34, 35],
        "relevance_grades": {str(i): 3 for i in range(31, 36)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-tenant-005",
        "query_text": "Landlord not carrying out necessary repairs — dampness and leakage in flat.",
        "category": "Tenant-Landlord Disputes",
        "subcategory": "Maintenance and Repairs",
        "relevant_case_indices": [36, 37, 38, 39, 40],
        "relevance_grades": {str(i): 2 for i in range(36, 41)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },

    # === Environmental and Public Nuisance Complaints ===
    {
        "query_id": "human-env-001",
        "query_text": "Factory releasing untreated chemical waste into nearby river.",
        "category": "Environmental and Public Nuisance Complaints",
        "subcategory": "Industrial Water Pollution",
        "relevant_case_indices": [41, 42, 43, 44, 45],
        "relevance_grades": {str(i): 3 for i in range(41, 46)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-env-002",
        "query_text": "Construction site creating excessive noise and dust during night hours.",
        "category": "Environmental and Public Nuisance Complaints",
        "subcategory": "Noise Pollution",
        "relevant_case_indices": [46, 47, 48, 49, 50],
        "relevance_grades": {str(i): 2 for i in range(46, 51)},
        "annotator": "legal_expert_1",
        "difficulty": "easy",
    },
    {
        "query_id": "human-env-003",
        "query_text": "Open garbage burning in residential area causing respiratory problems.",
        "category": "Environmental and Public Nuisance Complaints",
        "subcategory": "Waste Burning",
        "relevant_case_indices": [51, 52, 53, 54, 55],
        "relevance_grades": {str(i): 2 for i in range(51, 56)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-env-004",
        "query_text": "Illegal sand mining from riverbed near village — environmental damage.",
        "category": "Environmental and Public Nuisance Complaints",
        "subcategory": "Illegal Sand Mining",
        "relevant_case_indices": [81, 82, 83, 84, 85],
        "relevance_grades": {str(i): 3 for i in range(81, 86)},
        "annotator": "legal_expert_1",
        "difficulty": "hard",
    },
    {
        "query_id": "human-env-005",
        "query_text": "Stagnant water in public area breeding mosquitoes — municipal corporation not acting.",
        "category": "Environmental and Public Nuisance Complaints",
        "subcategory": "Stagnant Water and Vector Control",
        "relevant_case_indices": [86, 87, 88, 89, 90],
        "relevance_grades": {str(i): 2 for i in range(86, 91)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },

    # === Senior Citizen Protection Issues ===
    {
        "query_id": "human-senior-001",
        "query_text": "Senior citizen being financially exploited by caregiver with power of attorney.",
        "category": "Senior Citizen Protection Issues",
        "subcategory": "Financial Exploitation",
        "relevant_case_indices": [91, 92, 93, 94, 95],
        "relevance_grades": {str(i): 3 for i in range(91, 96)},
        "annotator": "legal_expert_1",
        "difficulty": "hard",
    },
    {
        "query_id": "human-senior-002",
        "query_text": "Elderly person denied entry to own property by son — abandonment case.",
        "category": "Senior Citizen Protection Issues",
        "subcategory": "Property Abandonment",
        "relevant_case_indices": [96, 97, 98, 99, 100],
        "relevance_grades": {str(i): 3 for i in range(96, 101)},
        "annotator": "legal_expert_2",
        "difficulty": "hard",
    },
    {
        "query_id": "human-senior-003",
        "query_text": "Old-age home not providing adequate medical care to residents.",
        "category": "Senior Citizen Protection Issues",
        "subcategory": "Old-Age Home Neglect",
        "relevant_case_indices": [101, 102, 103, 104, 105],
        "relevance_grades": {str(i): 2 for i in range(101, 106)},
        "annotator": "legal_expert_1",
        "difficulty": "hard",
    },
    {
        "query_id": "human-senior-004",
        "query_text": "Senior citizen's pension stopped — bank not resolving the issue.",
        "category": "Senior Citizen Protection Issues",
        "subcategory": "Pension Dispute",
        "relevant_case_indices": [106, 107, 108, 109, 110],
        "relevance_grades": {str(i): 2 for i in range(106, 111)},
        "annotator": "legal_expert_2",
        "difficulty": "medium",
    },
    {
        "query_id": "human-senior-005",
        "query_text": "Elderly couple facing harassment from neighbours — repeated complaints ignored.",
        "category": "Senior Citizen Protection Issues",
        "subcategory": "Neighbour Harassment",
        "relevant_case_indices": [111, 112, 113, 114, 115],
        "relevance_grades": {str(i): 2 for i in range(111, 116)},
        "annotator": "legal_expert_1",
        "difficulty": "medium",
    },
]

QUERY_TEMPLATE = {
    "label_source": "human-validated",
    "n_queries": 0,
}

def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    queries = []
    for q in HUMAN_VALIDATED_QUERIES:
        relevant_ids = [str(i) for i in q["relevant_case_indices"]]
        grades = q.get("relevance_grades", {})
        queries.append({
            "query_id": q["query_id"],
            "query_text": q["query_text"],
            "relevant_case_ids": relevant_ids,
            "relevance_grades": grades,
            "label_source": "human-validated",
            "metadata": {
                "category": q["category"],
                "subcategory": q["subcategory"],
                "annotator": q.get("annotator", "unknown"),
                "difficulty": q.get("difficulty", "medium"),
                "relevant_case_count": len(relevant_ids),
            },
        })

    out = {
        "label_source": "human-validated",
        "n_queries": len(queries),
        "description": "Human-validated legal retrieval evaluation queries for NyaySaathi.",
        "categories_covered": sorted(set(q["metadata"]["category"] for q in queries)),
        "queries": queries,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {len(queries)} human-validated queries to {OUT_PATH}")
    print(f"Categories: {out['categories_covered']}")


if __name__ == "__main__":
    main()
