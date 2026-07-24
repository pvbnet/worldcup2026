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
# 2023 edition was postponed and played in Jan 2024.
ASIAN_CUP_EDITIONS: dict[int, list[int]] = {2019: [2019], 2023: [2024]}
GOLD_CUP_EDITIONS: dict[int, list[int]] = {
    2019: [2019],
    2021: [2021],
    2023: [2023],
    2025: [2025],
}
# Friendlies have no real "edition" concept: one file per calendar year,
# matching the same 2018-2026 window used for the rest of training data.
FRIENDLY_YEARS: list[int] = list(range(2018, CURRENT_YEAR + 1))
FRIENDLY_EDITIONS: dict[int, list[int]] = {year: [year] for year in FRIENDLY_YEARS}

# Match-importance weight applied to Elo updates: World Cup finals count
# most, then continental championships, then qualifiers, then friendlies.
COMPETITION_WEIGHTS: dict[str, float] = {
    "world_cup": 1.0,
    "euro": 0.8,
    "copa_america": 0.8,
    "afcon": 0.8,
    "afc_asian_cup": 0.8,
    "gold_cup": 0.8,
    "wc_qualifier": 0.6,
    "friendly": 0.2,
}

# Match-outcome strength source: trained Elo ratings or FIFA pseudo-Elo
DEFAULT_STRENGTH = "elo"
STRENGTH_SOURCES = ("elo", "fifa")

# Tournament-stage cutoff: which real 2026 World Cup results are "known" (used
# for training + locked in as fixed outcomes) vs. left for Monte Carlo
# simulation. Ordered from earliest to latest.
STAGE_PRE_TOURNAMENT = "pre_tournament"
STAGE_GROUP = "group"
STAGE_R32 = "r32"
STAGE_R16 = "r16"
STAGE_QF = "qf"
STAGE_SF = "sf"
STAGE_COMPLETE = "complete"

STAGE_ORDER: list[str] = [
    STAGE_PRE_TOURNAMENT,
    STAGE_GROUP,
    STAGE_R32,
    STAGE_R16,
    STAGE_QF,
    STAGE_SF,
    STAGE_COMPLETE,
]
DEFAULT_STAGE = STAGE_PRE_TOURNAMENT

# Which per-match `stage` values (see ingest.infer_stage) of the *current*
# World Cup year are considered "known" at each cutoff, for training-data
# filtering and for deciding which real knockout rounds are locked in.
STAGE_INCLUDED_MATCH_STAGES: dict[str, set[str]] = {
    STAGE_PRE_TOURNAMENT: set(),
    STAGE_GROUP: {"group"},
    STAGE_R32: {"group", "r32"},
    STAGE_R16: {"group", "r32", "r16"},
    STAGE_QF: {"group", "r32", "r16", "qf"},
    STAGE_SF: {"group", "r32", "r16", "qf", "sf"},
    STAGE_COMPLETE: {"group", "r32", "r16", "qf", "sf", "final", "third"},
}

# Ordered knockout rounds used to build/walk the real 2026 bracket tree.
KNOCKOUT_ROUND_ORDER: list[str] = ["r32", "r16", "qf", "sf", "final"]

STAGE_LABELS: dict[str, str] = {
    STAGE_PRE_TOURNAMENT: "Pre-tournament",
    STAGE_GROUP: "Group stage done",
    STAGE_R32: "Round of 32 done",
    STAGE_R16: "Round of 16 done",
    STAGE_QF: "Quarterfinals done",
    STAGE_SF: "Semifinals done",
    STAGE_COMPLETE: "Tournament complete",
}

STAGE_DESCRIPTIONS: dict[str, str] = {
    STAGE_PRE_TOURNAMENT: (
        "Train and simulate using only data from before the tournament; "
        "the entire tournament (including groups) is simulated."
    ),
    STAGE_GROUP: (
        "Group stage results are fixed to the real outcome; "
        "Round of 32 onward is simulated."
    ),
    STAGE_R32: (
        "Group stage and Round of 32 results are fixed to the real outcome; "
        "Round of 16 onward is simulated."
    ),
    STAGE_R16: (
        "Group stage through Round of 16 are fixed to the real outcome; "
        "Quarterfinals onward is simulated."
    ),
    STAGE_QF: (
        "Group stage through Quarterfinals are fixed to the real outcome; "
        "Semifinals and Final are simulated."
    ),
    STAGE_SF: (
        "Group stage through Semifinals are fixed to the real outcome; "
        "only the Final is simulated."
    ),
    STAGE_COMPLETE: (
        "The tournament is over; all results are real (no simulation)."
    ),
}

# Bracket data specific to the 2026 World Cup's 48-team / 12-group format.
WC2026_BRACKET_DATA = MODEL_ROOT / "data" / "wc2026_r32_bracket.json"

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
    "afc_asian_cup": {
        "folder": "afc_asian_cup",
        "file_stem": "afc_asian_cup",
        "editions": ASIAN_CUP_EDITIONS,
        "raw_subdir": "asian_cup",
        "display_name": "AFC Asian Cup",
    },
    "gold_cup": {
        "folder": "gold_cup",
        "file_stem": "gold_cup",
        "editions": GOLD_CUP_EDITIONS,
        "raw_subdir": "gold_cup",
        "display_name": "CONCACAF Gold Cup",
    },
    "friendly": {
        "folder": "friendly",
        "file_stem": "friendly",
        "editions": FRIENDLY_EDITIONS,
        "raw_subdir": "friendly",
        "display_name": "International Friendly",
        "default_stage": "friendly",
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
