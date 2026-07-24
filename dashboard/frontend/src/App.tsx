import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useState } from "react";
import { useDashboard } from "./hooks/useApi";
import { Stage, Strength } from "./api/client";
import { StageSelector } from "./components/Dashboard";
import { RankingsPage } from "./pages/RankingsPage";
import { GroupsPage } from "./pages/GroupsPage";
import { BracketPage } from "./pages/BracketPage";

export default function App() {
  const [strength, setStrength] = useState<Strength>("elo");
  const [stage, setStage] = useState<Stage>("pre_tournament");
  const [simulations, setSimulations] = useState(1000);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const {
    teams,
    matches,
    groups,
    simulating,
    progress,
    progressMessage,
    error,
    refresh,
  } = useDashboard(strength, simulations, stage);

  return (
    <div className="app">
      <header>
        <div>
          <h1>World Cup 2026 Predictive Dashboard</h1>
          <p>
            Championship odds from Monte Carlo sims driven by either trained Elo
            ratings or FIFA rankings.
          </p>
          <nav className="top-nav">
            <NavLink to="/" end>
              Groups &amp; teams
            </NavLink>
            <NavLink to="/knockout">Knockout Stage</NavLink>
            <NavLink to="/predictions">Predictions</NavLink>
          </nav>
        </div>
        <div className="header-actions">
          <StageSelector stage={stage} onChange={setStage} disabled={simulating} />
          <button onClick={refresh} disabled={simulating}>
            {simulating ? "Simulating…" : "Refresh data"}
          </button>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <main>
        <Routes>
          <Route
            path="/"
            element={
              <GroupsPage
                teams={teams}
                matches={matches}
                groups={groups}
                stage={stage}
                selectedTeam={selectedTeam}
                onSelectTeam={setSelectedTeam}
              />
            }
          />
          <Route
            path="/knockout"
            element={<BracketPage matches={matches} stage={stage} />}
          />
          <Route
            path="/predictions"
            element={
              <RankingsPage
                strength={strength}
                onStrengthChange={setStrength}
                stage={stage}
                simulations={simulations}
                onSimulationsChange={setSimulations}
                teams={teams}
                simulating={simulating}
                progress={progress}
                progressMessage={progressMessage}
                selectedTeam={selectedTeam}
                onSelectTeam={setSelectedTeam}
              />
            }
          />
          <Route path="/groups" element={<Navigate to="/" replace />} />
          <Route path="/bracket" element={<Navigate to="/knockout" replace />} />
        </Routes>
      </main>
    </div>
  );
}
