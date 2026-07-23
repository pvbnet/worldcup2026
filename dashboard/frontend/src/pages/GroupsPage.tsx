import { GroupStandings, TeamDetailPanel } from "../components/Dashboard";
import { MatchRow, TeamPrediction } from "../api/client";

interface Props {
  teams: TeamPrediction[];
  matches: MatchRow[];
  groups: Record<string, unknown[]>;
  selectedTeam: string | null;
  onSelectTeam: (team: string) => void;
}

export function GroupsPage({
  teams,
  matches,
  groups,
  selectedTeam,
  onSelectTeam,
}: Props) {
  const selected = teams.find((t) => t.team === selectedTeam) ?? null;

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
      <TeamDetailPanel team={selected} matches={matches} />
      <GroupStandings groups={groups} />
    </section>
  );
}
