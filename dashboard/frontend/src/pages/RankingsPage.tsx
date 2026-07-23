import {
  RankingsTable,
  SimCountControl,
  SimulationOverlay,
  StrengthToggle,
} from "../components/Dashboard";
import { Strength, TeamPrediction } from "../api/client";

interface Props {
  strength: Strength;
  onStrengthChange: (value: Strength) => void;
  simulations: number;
  onSimulationsChange: (value: number) => void;
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
  simulations,
  onSimulationsChange,
  teams,
  simulating,
  progress,
  progressMessage,
  selectedTeam,
  onSelectTeam,
}: Props) {
  return (
    <>
      <div className="page-toolbar">
        <StrengthToggle
          strength={strength}
          onChange={onStrengthChange}
          disabled={simulating}
        />
        <SimCountControl
          value={simulations}
          onChange={onSimulationsChange}
          disabled={simulating}
        />
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
      <p className="predictions-footnote">
        Round of 16: each trial takes the top 2 from every group (24 teams),
        ranks them by the active strength ratings (Elo or FIFA), and keeps the
        top 16 for an Elo-seeded knockout bracket. There is no separate Round of
        32 in the simulator — P(R32) is the chance of finishing top-2 in the
        group.
      </p>
    </>
  );
}
