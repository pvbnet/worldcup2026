import {
  RankingsTable,
  SimCountControl,
  SimulationOverlay,
  StrengthToggle,
} from "../components/Dashboard";
import { SimMode, Stage, Strength, TeamPrediction } from "../api/client";

const STRENGTH_HELP =
  "Predict tournament outcomes using Monte Carlo simulations based on trained Elo ratings or FIFA rankings.";

const STAGE_HELP: Record<Stage, string> = {
  pre_tournament:
    "Every stage is Monte Carlo simulated using only " +
    "pre-tournament data — no 2026 results are used.",
  group:
    "Group stage results and entry to the round of 32 are fixed based on " +
    "the real outcome. Round of 32 onward is Monte Carlo simulated.",
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

interface Props {
  strength: Strength;
  onStrengthChange: (value: Strength) => void;
  stage: Stage;
  simMode: SimMode;
  onSimModeChange: (value: SimMode) => void;
  teams: TeamPrediction[];
  simulating: boolean;
  progress: number;
  progressMessage: string;
  selectedTeam: string | null;
  onSelectTeam: (team: string) => void;
}

export function RankingsPage({
  strength,
  onStrengthChange,
  stage,
  simMode,
  onSimModeChange,
  teams,
  simulating,
  progress,
  progressMessage,
  selectedTeam,
  onSelectTeam,
}: Props) {
  return (
    <>
      <div className="panel predictions-intro">
        <h2>Tournament Predictions</h2>
        <p>{STRENGTH_HELP}</p>
        <p>{STAGE_HELP[stage]}</p>
        <div className="page-toolbar">
          <StrengthToggle
            strength={strength}
            onChange={onStrengthChange}
            disabled={simulating}
          />
          <SimCountControl
            value={simMode}
            onChange={onSimModeChange}
            disabled={simulating}
          />
        </div>
      </div>
      <SimulationOverlay
        visible={simulating}
        progress={progress}
        message={progressMessage}
      />
      <RankingsTable
        teams={teams}
        selectedTeam={selectedTeam}
        onSelect={onSelectTeam}
      />
    </>
  );
}
