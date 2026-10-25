# Fertilizer calculation engine (no machine learning, just agronomy arithmetic)
#
# IMPORTANT: DOSES and ADJUST hold PLACEHOLDER numbers.
# Replace them with values from MPKV Rahuri / your KVK / the Maharashtra
# agriculture department, and write the source next to each one.

ACRE_PER_HECTARE = 2.471
BAG_KG = 50                      # one fertilizer bag = 50 kg

# Soil Health Card ratings in kg/ha: (below first = low, above second = high)
LIMITS = {"N": (280, 560), "P": (10, 25), "K": (120, 280)}

# PLACEHOLDER: change of dose for each soil rating (replace with an official rule)
ADJUST = {"low": 1.25, "medium": 1.0, "high": 0.75}

# Recommended dose in kg/ha of N, P2O5, K2O for each crop.
DOSES = {
    "Example crop (placeholder)": {
        "N": 100, "P2O5": 50, "K2O": 50,
        "source": "PLACEHOLDER - replace with a real recommendation",
    },
    # "Cotton": {"N": ..., "P2O5": ..., "K2O": ..., "source": "who, where, year"},
    # "Soybean": {...},
}

# Fertilizer contents (standard)
UREA_N = 0.46        # urea = 46% nitrogen
DAP_N = 0.18         # DAP = 18% nitrogen
DAP_P2O5 = 0.46      # DAP = 46% phosphorus (P2O5)
MOP_K2O = 0.60       # MOP = 60% potassium (K2O)


def rate_soil(nutrient, value):
    low, high = LIMITS[nutrient]
    if value < low:
        return "low"
    elif value <= high:
        return "medium"
    else:
        return "high"


def fertilizer_plan(dose, soil):
    # dose = {"N":..., "P2O5":..., "K2O":...} in kg/ha
    # soil = {"N":..., "P":..., "K":...} soil test in kg/ha
    ratings = {
        "N": rate_soil("N", soil["N"]),
        "P": rate_soil("P", soil["P"]),
        "K": rate_soil("K", soil["K"]),
    }

    need_n = dose["N"] * ADJUST[ratings["N"]]
    need_p = dose["P2O5"] * ADJUST[ratings["P"]]
    need_k = dose["K2O"] * ADJUST[ratings["K"]]

    dap = need_p / DAP_P2O5                         # DAP supplies the phosphorus
    n_from_dap = dap * DAP_N                        # and some nitrogen too
    urea = max(need_n - n_from_dap, 0) / UREA_N     # urea covers the rest of the nitrogen
    mop = need_k / MOP_K2O

    per_ha = {"Urea": urea, "DAP": dap, "MOP": mop}
    per_acre = {name: kg / ACRE_PER_HECTARE for name, kg in per_ha.items()}
    return {
        "ratings": ratings,
        "needs": {"N": need_n, "P2O5": need_p, "K2O": need_k},
        "per_ha": per_ha,
        "per_acre": per_acre,
    }