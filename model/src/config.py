from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = PROJECT_ROOT / "model"

DATA_RAW = MODEL_ROOT / "data" / "raw"
DATA_PROCESSED = MODEL_ROOT / "data" / "processed"
ARTIFACTS_TRAINING = MODEL_ROOT / "artifacts" / "training"
ARTIFACTS_EVALUATION = MODEL_ROOT / "artifacts" / "evaluation"
ARTIFACTS_PREDICTIONS = MODEL_ROOT / "artifacts" / "predictions"

HISTORICAL_YEARS = [2018, 2022]
CURRENT_YEAR = 2026
ALL_YEARS = HISTORICAL_YEARS + [CURRENT_YEAR]

OPENFOOTBALL_BASE = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master"
)
INTERNATIONALS_BASE = (
    "https://raw.githubusercontent.com/openfootball/internationals/master"
)

# edition_label -> list of source file years to download/merge
EURO_EDITIONS: dict[int, list[int]] = {2020: [2021], 2024: [2024]}
COPA_AMERICA_EDITIONS: dict[int, list[int]] = {2021: [2021], 2024: [2024]}
AFCON_EDITIONS: dict[int, list[int]] = {
    2021: [2022],
    2023: [2024],
    2025: [2025, 2026],
}
WC_QUALIFIER_CYCLES: dict[int, list[int]] = {
    2022: [2019, 2020, 2021, 2022],
    2026: [2023, 2024, 2025, 2026],
}

# World Football Elo Ratings importance: WC finals=60, continental=50, qualifiers=40
COMPETITION_WEIGHTS: dict[str, float] = {
    "world_cup": 1.0,
    "euro": 50 / 60,
    "copa_america": 50 / 60,
    "afcon": 50 / 60,
    "wc_qualifier": 40 / 60,
}

# Match-outcome strength source: trained Elo ratings or FIFA pseudo-Elo
DEFAULT_STRENGTH = "elo"
STRENGTH_SOURCES = ("elo", "fifa")

COMPETITION_SOURCES: dict[str, dict] = {
    "euro": {
        "folder": "uefa_euro",
        "file_stem": "uefa_euro",
        "editions": EURO_EDITIONS,
        "raw_subdir": "euro",
        "display_name": "UEFA Euro",
    },
    "copa_america": {
        "folder": "copa_america",
        "file_stem": "copa_america",
        "editions": COPA_AMERICA_EDITIONS,
        "raw_subdir": "copa_america",
        "display_name": "Copa América",
    },
    "afcon": {
        "folder": "african_cup_of_nations",
        "file_stem": "african_cup_of_nations",
        "editions": AFCON_EDITIONS,
        "raw_subdir": "afcon",
        "display_name": "African Cup of Nations",
    },
    "wc_qualifier": {
        "folder": "fifa_world_cup_qualification",
        "file_stem": "fifa_world_cup_qualification",
        "editions": WC_QUALIFIER_CYCLES,
        "raw_subdir": "wc_qualifiers",
        "display_name": "FIFA World Cup qualification",
        "default_stage": "qualifier",
    },
}

for path in (
    DATA_RAW,
    DATA_PROCESSED,
    ARTIFACTS_TRAINING,
    ARTIFACTS_EVALUATION,
    ARTIFACTS_PREDICTIONS,
):
    path.mkdir(parents=True, exist_ok=True)

for meta in COMPETITION_SOURCES.values():
    (DATA_RAW / meta["raw_subdir"]).mkdir(parents=True, exist_ok=True)
