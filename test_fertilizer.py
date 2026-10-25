# Simple tests for fertilizer.py
# Run from the project root:  python -m tests.test_fertilizer
# The expected numbers were worked out by hand (see comments).

from fertilizer import rate_soil, fertilizer_plan

dose = {"N": 100, "P2O5": 50, "K2O": 50}

# --- Test 1: soil ratings follow the Soil Health Card limits ---
assert rate_soil("N", 250) == "low"
assert rate_soil("N", 300) == "medium"
assert rate_soil("N", 600) == "high"
assert rate_soil("P", 15) == "medium"
assert rate_soil("K", 300) == "high"

# --- Test 2: all medium soil -> dose unchanged ---
# DAP = 50 / 0.46 = 108.7 ; N from DAP = 108.7 * 0.18 = 19.57
# Urea = (100 - 19.57) / 0.46 = 174.9 ; MOP = 50 / 0.60 = 83.3
plan = fertilizer_plan(dose, {"N": 300, "P": 15, "K": 200})
assert round(plan["per_ha"]["DAP"], 1) == 108.7
assert round(plan["per_ha"]["Urea"], 1) == 174.9
assert round(plan["per_ha"]["MOP"], 1) == 83.3

# --- Test 3: low N, medium P, high K ---
# N need = 100 * 1.25 = 125 ; K need = 50 * 0.75 = 37.5
# Urea = (125 - 19.57) / 0.46 = 229.2 ; MOP = 37.5 / 0.60 = 62.5
plan = fertilizer_plan(dose, {"N": 250, "P": 15, "K": 300})
assert round(plan["per_ha"]["Urea"], 1) == 229.2
assert round(plan["per_ha"]["MOP"], 1) == 62.5

# --- Test 4: if DAP already gives all the nitrogen, urea must not go negative ---
plan = fertilizer_plan({"N": 10, "P2O5": 50, "K2O": 0}, {"N": 300, "P": 15, "K": 200})
assert plan["per_ha"]["Urea"] == 0

print("All tests passed")