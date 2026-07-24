import {
  RankingsTable,
  SimCountControl,
  SimulationOverlay,
  StrengthToggle,
  stageFootnote,
} from "../components/Dashboard";
import { Stage, Strength, TeamPrediction } from "../api/client";

interface Props {
  strength: Strength;
  onStrengthChange: (value: Strength) => void;
  stage: Stage;
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
  stage,
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
      <p className="predictions-footnote">{stageFootnote(stage)}</p>
    </>
  );
}
