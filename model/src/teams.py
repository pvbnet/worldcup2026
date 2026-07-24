TEAM_ALIASES: dict[str, str] = {
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "USA": "United States",
    "US": "United States",
    "IR Iran": "Iran",
    "Cabo Verde": "Cape Verde",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "China PR": "China",
    "PR China": "China",
    "Czechia": "Czech Republic",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Curacao": "Curaçao",
    "FYR Macedonia": "North Macedonia",
    "Macedonia": "North Macedonia",
    "Rep. of Ireland": "Republic of Ireland",
    "Brunei Darussalam": "Brunei",
    "Swaziland": "Eswatini",
    "eSwatini": "Eswatini",
    "Kyrgyz Republic": "Kyrgyzstan",
    "Korea DPR": "North Korea",
    "St. Kitts and Nevis": "Saint Kitts and Nevis",
    "St Kitts and Nevis": "Saint Kitts and Nevis",
    "St. Lucia": "Saint Lucia",
    "St Lucia": "Saint Lucia",
    "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "St Vincent and the Grenadines": "Saint Vincent and the Grenadines",
    "Chinese Taipei": "Taiwan",
    "US Virgin Islands": "United States Virgin Islands",
}


def canonicalize(name: str) -> str:
    name = name.strip()
    return TEAM_ALIASES.get(name, name)


def is_placeholder(name: str) -> bool:
    name = name.strip()
    if not name:
        return True
    if name[0] in ("W", "L") and len(name) >= 2 and name[1:].isdigit():
        return True
    if name.startswith("Winner ") or name.startswith("Loser "):
        return True
    if len(name) <= 4 and name[0].isdigit() and name[1:2].isalpha():
        return True
    if "/" in name and name[0].isdigit():
        return True
    return False
