import { GroupStandings, TeamDetailPanel } from "../components/Dashboard";
import { MatchRow, Stage, TeamPrediction } from "../api/client";

interface Props {
  teams: TeamPrediction[];
  matches: MatchRow[];
  groups: Record<string, unknown[]>;
  stage: Stage;
  selectedTeam: string | null;
  onSelectTeam: (team: string) => void;
}

interface GroupRow {
  team: string;
  points: number;
  gd: number;
}

// Pre-tournament: no real results are knowable yet, so build the group view
// straight from each team's assigned group with 0 points/0 GD instead of
// using the (not stage-aware) real standings from the API.
function buildPreTournamentGroups(
  teams: TeamPrediction[]
): Record<string, GroupRow[]> {
  const groups: Record<string, GroupRow[]> = {};
  for (const t of teams) {
    const key = t.group ?? "Unassigned";
    (groups[key] ??= []).push({ team: t.team, points: 0, gd: 0 });
  }
  for (const rows of Object.values(groups)) {
    rows.sort((a, b) => a.team.localeCompare(b.team));
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
  const selected = teams.find((t) => t.team === selectedTeam) ?? null;
  const isPreTournament = stage === "pre_tournament";
  const displayGroups = isPreTournament
    ? buildPreTournamentGroups(teams)
    : groups;

  return (
    <section className="bottom-grid">
      <div className="panel">
        <h2>Select a team</h2>
        <div className="team-chips">
          {teams.map((t) => (
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
            ? "2026 Group Assignments (Tournament Not Started)"
            : "2026 Group Standings (Played Matches)"
        }
      />
    </section>
  );
}
