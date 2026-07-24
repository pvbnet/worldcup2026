import { GroupStandings, TeamDetailPanel } from "../components/Dashboard";
import { MatchRow, Stage, TeamPrediction } from "../api/client";

interface Props {
  teams: TeamPrediction[];
  matches: MatchRow[];
  groups: Record<string, unknown[]>;
  stage: Stage;
  selectedTeam: string | null;
  onSelectTeam: (team: string | null) => void;
}

interface GroupRow {
  team: string;
  points: number;
  gd: number;
}

function sortTeamsByFifaRank(teams: TeamPrediction[]): TeamPrediction[] {
  return [...teams].sort((a, b) => {
    const diff = a.fifa_rank - b.fifa_rank;
    if (diff !== 0) return diff;
    return a.team.localeCompare(b.team);
  });
}

// Pre-tournament: no real results are knowable yet, so build the group view
// straight from each team's assigned group with 0 points/0 GD instead of
// using the (not stage-aware) real standings from the API.
function buildPreTournamentGroups(
  teams: TeamPrediction[]
): Record<string, GroupRow[]> {
  const groups: Record<string, GroupRow[]> = {};
  for (const t of sortTeamsByFifaRank(teams)) {
    const key = t.group ?? "Unassigned";
    (groups[key] ??= []).push({ team: t.team, points: 0, gd: 0 });
  }
  return groups;
}

export function GroupsPage({
  teams,
  matches,
  groups,
  stage,
  selectedTeam,
  onSelectTeam,
}: Props) {
  const teamsOrdered = sortTeamsByFifaRank(teams);
  const selected = teamsOrdered.find((t) => t.team === selectedTeam) ?? null;
  const isPreTournament = stage === "pre_tournament";
  const displayGroups = isPreTournament
    ? buildPreTournamentGroups(teamsOrdered)
    : groups;

  return (
    <section className="bottom-grid">
      <div className="panel">
        <h2>Teams</h2>
        <div className="team-chips">
          <button
            type="button"
            className={selectedTeam === null ? "active" : ""}
            onClick={() => onSelectTeam(null)}
          >
            None
          </button>
          {teamsOrdered.map((t) => (
            <button
              key={t.team}
              type="button"
              className={selectedTeam === t.team ? "active" : ""}
              onClick={() => onSelectTeam(t.team)}
            >
              {t.team}
            </button>
          ))}
        </div>
      </div>
      <TeamDetailPanel team={selected} matches={matches} stage={stage} />
      <GroupStandings
        groups={displayGroups}
        title={
          isPreTournament
            ? "2026 Group Standings (Pre-Tournament)"
            : "2026 Group Standings"
        }
      />
    </section>
  );
}
