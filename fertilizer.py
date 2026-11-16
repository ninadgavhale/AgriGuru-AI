

ACRE_PER_HECTARE = 2.471
BAG_KG = 50                     


LIMITS = {"N": (280, 560), "P": (10, 25), "K": (120, 280)}


ADJUST = {"low": 1.25, "medium": 1.0, "high": 0.75}


DOSES = {
    "Wheat": {"N": 120, "P2O5": 60, "K2O": 40,
              "source": "MPKV Rahuri, Agricultural Research Recommendations 2025 (item 11): "
                        "irrigated wheat, medium deep black soils of Western Maharashtra, with FYM"},
    "Soybean": {"N": 50, "P2O5": 75, "K2O": 45,
                "source": "MPKV Rahuri, Agricultural Research Recommendations 2025 (item 13): "
                          "sub-Montane Zone of Maharashtra, with 10 t/ha FYM and chelated Zn spray"},
    "Chickpea": {"N": 25, "P2O5": 50, "K2O": 0,
                 "source": "MPKV Rahuri chickpea recommendations: 25 kg N + 50 kg P2O5 per ha "
                           "(no potash recommended)"},
    "Sunflower": {"N": 60, "P2O5": 90, "K2O": 60,
                  "source": "MPKV Rahuri, ARS Savalvihir recommendations: GRDF 60:90:60 for "
                            "kharif rainfed sunflower, Western Maharashtra"},
    "Cotton": {"N": 100, "P2O5": 50, "K2O": 50,
               "source": "RDF 100:50:50 + 10 t FYM used as the MPKV Rahuri recommended dose in "
                         "MPKV research paper (clrri.org, hybrid cotton); verify with MPKV/KVK"},
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

    dap = need_p / DAP_P2O5                         
    n_from_dap = dap * DAP_N                        
    urea = max(need_n - n_from_dap, 0) / UREA_N     
    mop = need_k / MOP_K2O

    per_ha = {"Urea": urea, "DAP": dap, "MOP": mop}
    per_acre = {name: kg / ACRE_PER_HECTARE for name, kg in per_ha.items()}
    return {
        "ratings": ratings,
        "needs": {"N": need_n, "P2O5": need_p, "K2O": need_k},
        "per_ha": per_ha,
        "per_acre": per_acre,
    }
