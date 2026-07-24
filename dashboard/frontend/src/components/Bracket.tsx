import { MatchRow, Stage, STAGE_INCLUDED_MATCH_STAGES } from "../api/client";

type KnockoutStage = "r32" | "r16" | "qf" | "sf";
type RoundMode = "full" | "entry" | "hidden";

const ALL_KO_ROUNDS: readonly string[] = ["r32", "r16", "qf", "sf", "final"];

// For each knockout round (plus "third"), decide whether to render it with
// real scores ("full"), real team names but a hidden result ("entry" — the
// first round beyond the stage cutoff), or a blank TBD placeholder
// ("hidden" — further rounds, whose participants aren't "knowable" yet at
// this cutoff).
function roundModes(stage: Stage): Record<string, RoundMode> {
  const included = STAGE_INCLUDED_MATCH_STAGES[stage];
  const modes: Record<string, RoundMode> = {};
  let entryAssigned = false;
  for (const round of ALL_KO_ROUNDS) {
    if (included.has(round)) {
      modes[round] = "full";
    } else if (!entryAssigned) {
      modes[round] = "entry";
      entryAssigned = true;
    } else {
      modes[round] = "hidden";
    }
  }
  modes.third = included.has("third")
    ? "full"
    : modes.sf === "full"
      ? "entry"
      : "hidden";
  return modes;
}

function maskMatch(match: MatchRow, mode: RoundMode): MatchRow {
  if (mode === "full") return match;
  return {
    ...match,
    team1: mode === "hidden" ? "TBD" : match.team1,
    team2: mode === "hidden" ? "TBD" : match.team2,
    played: false,
    advancer: null,
    goals1: null,
    goals2: null,
    et1: null,
    et2: null,
    pen1: null,
    pen2: null,
  };
}

function maskRoundMatches(matches: MatchRow[], mode: RoundMode): MatchRow[] {
  return matches.map((m) => maskMatch(m, mode));
}

const STAGE_LABELS: Record<string, string> = {
  r32: "Round of 32",
  r16: "Round of 16",
  qf: "Quarter-finals",
  sf: "Semi-finals",
  final: "Final",
  third: "Third place",
};

const LEFT_ORDER: KnockoutStage[] = ["r32", "r16", "qf", "sf"];
const RIGHT_ORDER: KnockoutStage[] = ["sf", "qf", "r16", "r32"];
const PATH_STAGES: KnockoutStage[] = ["sf", "qf", "r16", "r32"];

function isThirdPlace(m: MatchRow): boolean {
  if (m.stage === "third") return true;
  const round = (m.round || "").toLowerCase();
  return round.includes("third") || round.includes("3rd");
}

function sortByDate(a: MatchRow, b: MatchRow): number {
  return String(a.date).localeCompare(String(b.date));
}

function collectHalf(
  anchor: string,
  byStage: Record<KnockoutStage, MatchRow[]>
): Record<KnockoutStage, MatchRow[]> {
  const teams = new Set<string>([anchor]);
  const half: Record<KnockoutStage, MatchRow[]> = {
    r32: [],
    r16: [],
    qf: [],
    sf: [],
  };

  for (const stage of PATH_STAGES) {
    const stageMatches = byStage[stage].filter(
      (m) => teams.has(m.team1) || teams.has(m.team2)
    );
    half[stage] = [...stageMatches].sort(sortByDate);
    for (const m of stageMatches) {
      teams.add(m.team1);
      teams.add(m.team2);
    }
  }
  return half;
}

export function buildBracket(matches: MatchRow[]) {
  const byStageList = (stage: string) =>
    matches.filter((m) => m.stage === stage).sort(sortByDate);

  const byStage: Record<KnockoutStage, MatchRow[]> = {
    r32: byStageList("r32"),
    r16: byStageList("r16"),
    qf: byStageList("qf"),
    sf: byStageList("sf"),
  };

  const finalMatch = byStageList("final")[0] ?? null;
  const thirdMatch =
    matches.filter(isThirdPlace).sort(sortByDate)[0] ?? null;

  let left: Record<KnockoutStage, MatchRow[]> = {
    r32: [],
    r16: [],
    qf: [],
    sf: [],
  };
  let right: Record<KnockoutStage, MatchRow[]> = {
    r32: [],
    r16: [],
    qf: [],
    sf: [],
  };

  if (finalMatch) {
    left = collectHalf(finalMatch.team1, byStage);
    right = collectHalf(finalMatch.team2, byStage);
  } else if (byStage.sf.length >= 2) {
    // Fallback if final missing: first SF → left, second → right
    const sfs = byStage.sf;
    left = collectHalf(sfs[0].team1, byStage);
    right = collectHalf(sfs[1].team1, byStage);
  }

  return { left, right, finalMatch, thirdMatch };
}

function winnerSide(match: MatchRow): "team1" | "team2" | null {
  if (match.advancer === match.team1) return "team1";
  if (match.advancer === match.team2) return "team2";
  if (!match.played || match.goals1 == null || match.goals2 == null) {
    return null;
  }
  if (match.goals1 > match.goals2) return "team1";
  if (match.goals2 > match.goals1) return "team2";
  return null;
}

function MatchSlot({ match }: { match: MatchRow }) {
  const winner = winnerSide(match);
  const hasPens = match.pen1 != null && match.pen2 != null;
  const hasAet = match.et1 != null && match.et2 != null;
  const showAet =
    hasAet &&
    !hasPens &&
    (match.goals1 === match.goals2 ||
      match.et1 !== match.goals1 ||
      match.et2 !== match.goals2);
  return (
    <div className="bracket-match">
      <div className={`bracket-team${winner === "team1" ? " winner" : ""}`}>
        <span className="bracket-team-name">{match.team1}</span>
        <span className="bracket-team-score">
          {match.played && match.goals1 != null ? match.goals1 : ""}
        </span>
      </div>
      <div className={`bracket-team${winner === "team2" ? " winner" : ""}`}>
        <span className="bracket-team-name">{match.team2}</span>
        <span className="bracket-team-score">
          {match.played && match.goals2 != null ? match.goals2 : ""}
        </span>
      </div>
      {hasPens && (
        <div className="bracket-match-meta">
          p {match.pen1}–{match.pen2}
        </div>
      )}
      {showAet && (
        <div className="bracket-match-meta">
          aet {match.et1}–{match.et2}
        </div>
      )}
      {!match.played && <div className="bracket-match-meta">—</div>}
    </div>
  );
}

function BracketRound({
  label,
  matches,
}: {
  label: string;
  matches: MatchRow[];
}) {
  return (
    <div className="bracket-round">
      <h3 className="bracket-round-label">{label}</h3>
      <div className="bracket-round-matches">
        {matches.map((m, i) => (
          <MatchSlot key={`${m.date}-${m.team1}-${m.team2}-${i}`} match={m} />
        ))}
      </div>
    </div>
  );
}

function BracketHalf({
  side,
  rounds,
  modes,
}: {
  side: "left" | "right";
  rounds: Record<KnockoutStage, MatchRow[]>;
  modes: Record<string, RoundMode>;
}) {
  const order = side === "left" ? LEFT_ORDER : RIGHT_ORDER;
  return (
    <div className={`bracket-half bracket-half--${side}`}>
      {order.map((stage) => (
        <BracketRound
          key={stage}
          label={STAGE_LABELS[stage]}
          matches={maskRoundMatches(rounds[stage], modes[stage])}
        />
      ))}
    </div>
  );
}

export function Bracket({
  matches,
  stage,
}: {
  matches: MatchRow[];
  stage: Stage;
}) {
  const { left, right, finalMatch, thirdMatch } = buildBracket(matches);
  const hasAny =
    left.r32.length + right.r32.length > 0 || finalMatch || thirdMatch;

  if (!hasAny) {
    return (
      <div className="panel">
        <p>No knockout fixtures found for 2026.</p>
      </div>
    );
  }

  const modes = roundModes(stage);

  return (
    <div className="bracket-scroll">
      <div className="bracket">
        <BracketHalf side="left" rounds={left} modes={modes} />
        <div className="bracket-center">
          {finalMatch && (
            <BracketRound
              label={STAGE_LABELS.final}
              matches={[maskMatch(finalMatch, modes.final)]}
            />
          )}
          {thirdMatch && (
            <BracketRound
              label={STAGE_LABELS.third}
              matches={[maskMatch(thirdMatch, modes.third)]}
            />
          )}
        </div>
        <BracketHalf side="right" rounds={right} modes={modes} />
      </div>
    </div>
  );
}
