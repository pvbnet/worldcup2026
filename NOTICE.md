# Third-party content and data

This repository’s **source code** is licensed under the MIT License (see [LICENSE](LICENSE)).
The following **data and third-party content** are not covered by that license; use them
according to their upstream terms and this notice.

## Match data (openfootball)

World Cup finals and international competition match data are downloaded from:

- [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
- [openfootball/internationals](https://github.com/openfootball/internationals) (Football.TXT format)

Fetched by [`model/scripts/fetch_data.py`](model/scripts/fetch_data.py). Consult the upstream
repositories for their licensing and attribution requirements.

## FIFA World Ranking snapshots

Historical FIFA ranking snapshots used for seeding and the FIFA strength mode are stored in
[`model/data/fifa_rankings.json`](model/data/fifa_rankings.json). Each snapshot records its
source URL in that file. This project is **not affiliated with FIFA**. Ranking values are
factual data compiled for research and modeling.

## What is committed in this repository

| Path | Notes |
|------|--------|
| `model/data/raw/**/*.json` | Many continental, qualifier, and friendly raw files are committed for convenience. |
| `model/data/raw/2018.json`, `2022.json`, `2026.json` | **Not** committed (see `.gitignore`). Run `python scripts/fetch_data.py` from `model/` after clone. |
| `model/data/processed/matches.parquet` | **Not** committed. Produced by `python scripts/ingest.py`. |
| `model/artifacts/` | Pre-built Elo and prediction JSON (~300 KB) so the dashboard works without re-simulating. Regenerate with `train.py` / `simulate.py` or the dashboard **Refresh data** action. |
