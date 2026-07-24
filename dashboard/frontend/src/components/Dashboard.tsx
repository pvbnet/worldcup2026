import {
  STAGE_INCLUDED_MATCH_STAGES,
  STAGE_OPTIONS,
  Stage,
  Strength,
  TeamPrediction,
} from "../api/client";

function groupLetter(group: string | null | undefined): string {
  if (!group) return "—";
  return group.replace(/^Group\s+/i, "");
}

export function StageSelector({
  stage,
  onChange,
  disabled,
}: {
  stage: Stage;
  onChange: (value: Stage) => void;
  disabled?: boolean;
}) {
  return (
    <div className="stage-selector" role="group" aria-label="Tournament stage">
      <span className="strength-label">Tournament stage</span>
      <select
        value={stage}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as Stage)}
      >
        {STAGE_OPTIONS.map((opt) => (
          <option key={opt.id} value={opt.id}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function StrengthToggle({
  strength,
  onChange,
  disabled,
}: {
  strength: Strength;
  onChange: (value: Strength) => void;
  disabled?: boolean;
}) {
  return (
    <div className="strength-toggle" role="group" aria-label="Strength source">
      <span className="strength-label">Match outcomes</span>
      <div className="segmented">
        <button
          type="button"
          className={strength === "elo" ? "active" : ""}
          onClick={() => onChange("elo")}
          disabled={disabled}
        >
          Elo
        </button>
        <button
          type="button"
          className={strength === "fifa" ? "active" : ""}
          onClick={() => onChange("fifa")}
          disabled={disabled}
        >
          FIFA
        </button>
      </div>
      <p className="strength-help">
        Simulate match outcomes using trained Elo ratings or FIFA rankings.
      </p>
    </div>
  );
}

const SIM_COUNTS = [1000, 2000, 3000, 4000, 5000] as const;

export function SimCountControl({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className="sim-count-control" role="group" aria-label="Simulation count">
      <span className="strength-label">Monte Carlo runs</span>
      <div className="segmented">
        {SIM_COUNTS.map((n) => (
          <button
            key={n}
            type="button"
            className={value === n ? "active" : ""}
            onClick={() => onChange(n)}
            disabled={disabled}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SimulationOverlay({
  visible,
  progress,
  message,
}: {
  visible: boolean;
  progress: number;
  message: string;
}) {
  if (!visible) return null;
  const pct = Math.round(Math.min(1, Math.max(0, progress)) * 100);
  return (
    <div className="sim-overlay" role="status" aria-live="polite">
      <div className="sim-overlay-card">
        <p className="sim-overlay-title">Running Monte Carlo simulations…</p>
        <p className="sim-overlay-message">{message || "Starting…"}</p>
        <progress value={pct} max={100} />
        <span className="sim-overlay-pct">{pct}%</span>
      </div>
    </div>
  );
}

function pct(value: number | undefined): string {
  return `${((value ?? 0) * 100).toFixed(1)}%`;
}

const STAGE_FOOTNOTES: Record<Stage, string> = {
  pre_tournament:
    "Every stage below, including the group stage, is Monte Carlo simulated " +
    "using only pre-tournament data — no 2026 results are used.",
  group:
    "Group stage results are fixed to the real outcome. Round of 32 is " +
    "resolved from the real group standings (FIFA's third-place ranking " +
    "rules) and Round of 32 onward is simulated.",
  r32:
    "Group stage and Round of 32 results are fixed to the real outcome. " +
    "Round of 16 onward is simulated.",
  r16:
    "Group stage through Round of 16 are fixed to the real outcome. " +
    "Quarterfinals onward is simulated.",
  qf:
    "Group stage through Quarterfinals are fixed to the real outcome. " +
    "Semifinals and the Final are simulated.",
  sf:
    "Group stage through Semifinals are fixed to the real outcome. Only the " +
    "Final is simulated.",
  complete:
    "The tournament is over — every probability reflects the real, final " +
    "outcome (no simulation).",
};

export function stageFootnote(stage: Stage): string {
  return STAGE_FOOTNOTES[stage];
}

export function RankingsTable({
  teams,
  selectedTeam,
  onSelect,
}: {
  teams: TeamPrediction[];
  selectedTeam: string | null;
  onSelect: (team: string) => void;
}) {
  return (
    <div className="panel rankings-panel">
      <h2>Team Rankings</h2>
      <div className="rankings-table-wrap">
        <table className="rankings-table">
          <thead>
            <tr>
              <th>Model Rank</th>
              <th>Elo Rank</th>
              <th>FIFA Rank</th>
              <th>Team</th>
              <th>Group</th>
              <th>Elo</th>
              <th>P(R32)</th>
              <th>P(R16)</th>
              <th>P(QF)</th>
              <th>P(SF)</th>
              <th>P(Final)</th>
              <th>P(Win WC)</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((team) => (
              <tr
                key={team.team}
                className={selectedTeam === team.team ? "selected" : ""}
                onClick={() => onSelect(team.team)}
              >
                <td>{team.model_rank ?? team.rank}</td>
                <td>{team.elo_rank}</td>
                <td>{team.fifa_rank}</td>
                <td>{team.team}</td>
                <td>{groupLetter(team.group)}</td>
                <td>{team.rating.toFixed(0)}</td>
                <td>{pct(team.p_r32)}</td>
                <td>{pct(team.p_r16)}</td>
                <td>{pct(team.p_qf)}</td>
                <td>{pct(team.p_sf)}</td>
                <td>{pct(team.p_final)}</td>
                <td className="win-prob-cell">
                  <div className="win-prob-inline">
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${Math.max((team.p_win ?? 0) * 100, team.p_win > 0 ? 1 : 0)}%`,
                        }}
                      />
                    </div>
                    <span className="bar-value">{pct(team.p_win)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function GroupStandings({
  groups,
  title = "2026 Group Standings (Played Matches)",
}: {
  groups: Record<string, unknown[]>;
  title?: string;
}) {
  const entries = Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="panel">
      <h2>{title}</h2>
      <div className="groups-grid">
        {entries.map(([group, rows]) => (
          <div key={group} className="group-card">
            <h3>{group}</h3>
            <table>
              <thead>
                <tr>
                  <th>Team</th>
                  <th>Pts</th>
                  <th>GD</th>
                </tr>
              </thead>
              <tbody>
                {(rows as Array<{ team: string; points: number; gd: number }>).map(
                  (row) => (
                    <tr key={row.team}>
                      <td>{row.team}</td>
                      <td>{row.points}</td>
                      <td>{row.gd}</td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TeamDetailPanel({
  team,
  matches,
  stage,
}: {
  team: TeamPrediction | null;
  matches: Array<{
    team1: string;
    team2: string;
    goals1: number | null;
    goals2: number | null;
    played: boolean;
    date: string;
    stage?: string;
  }>;
  stage: Stage;
}) {
  if (!team) {
    return (
      <div className="panel detail-panel">
        <h2>Team Detail</h2>
        <p>Select a team to view details.</p>
      </div>
    );
  }

  const includedStages = STAGE_INCLUDED_MATCH_STAGES[stage];
  const recent = matches
    .filter(
      (m) =>
        m.played &&
        (m.team1 === team.team || m.team2 === team.team) &&
        (!m.stage || includedStages.has(m.stage))
    )
    .slice(-5);

  return (
    <div className="panel detail-panel">
      <h2>{team.team}</h2>
      <dl className="detail-grid">
        <div>
          <dt>Model Rank</dt>
          <dd>{team.model_rank ?? team.rank}</dd>
        </div>
        <div>
          <dt>Elo Rank</dt>
          <dd>{team.elo_rank}</dd>
        </div>
        <div>
          <dt>FIFA Rank</dt>
          <dd>{team.fifa_rank}</dd>
        </div>
        <div>
          <dt>Elo Rating</dt>
          <dd>{team.rating.toFixed(0)}</dd>
        </div>
        {team.active_rating !== undefined && (
          <div>
            <dt>Active Rating</dt>
            <dd>{team.active_rating.toFixed(0)}</dd>
          </div>
        )}
        <div>
          <dt>P(R32)</dt>
          <dd>{pct(team.p_r32)}</dd>
        </div>
        <div>
          <dt>P(R16)</dt>
          <dd>{pct(team.p_r16)}</dd>
        </div>
        <div>
          <dt>P(QF)</dt>
          <dd>{pct(team.p_qf)}</dd>
        </div>
        <div>
          <dt>P(SF)</dt>
          <dd>{pct(team.p_sf)}</dd>
        </div>
        <div>
          <dt>P(Final)</dt>
          <dd>{pct(team.p_final)}</dd>
        </div>
        <div>
          <dt>P(Win WC)</dt>
          <dd>{pct(team.p_win)}</dd>
        </div>
        <div>
          <dt>Group</dt>
          <dd>{groupLetter(team.group)}</dd>
        </div>
      </dl>
      <h3>Recent 2026 Matches</h3>
      <ul>
        {recent.length === 0 && <li>No played matches yet.</li>}
        {recent.map((m, idx) => (
          <li key={`${m.date}-${idx}`}>
            {m.date}: {m.team1} {m.goals1} - {m.goals2} {m.team2}
          </li>
        ))}
      </ul>
    </div>
  );
}
