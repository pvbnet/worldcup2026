import { useCallback, useEffect, useState } from "react";
import {
  fetchGroups,
  fetchMatches,
  fetchRankings,
  pollSimulation,
  startSimulation,
  MatchRow,
  RankingsResponse,
  SIM_MODE_CACHED,
  SimMode,
  Stage,
  Strength,
} from "../api/client";

export function useDashboard(strength: Strength, simMode: SimMode, stage: Stage) {
  const [payload, setPayload] = useState<RankingsResponse | null>(null);
  const [matches, setMatches] = useState<MatchRow[]>([]);
  const [groups, setGroups] = useState<Record<string, unknown[]>>({});
  const [simulating, setSimulating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadStatic = useCallback(async () => {
    const [matchRows, groupRows] = await Promise.all([
      fetchMatches(2026),
      fetchGroups(),
    ]);
    setMatches(matchRows);
    setGroups(groupRows);
  }, []);

  useEffect(() => {
    loadStatic().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load matches");
    });
  }, [loadStatic]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      if (simMode === SIM_MODE_CACHED) {
        setSimulating(false);
        setProgress(0);
        setProgressMessage("");
        try {
          const rankings = await fetchRankings(strength, stage);
          if (cancelled) return;
          setPayload(rankings);
        } catch (err) {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : "Failed to load rankings");
          }
        }
        return;
      }

      setSimulating(true);
      setProgress(0);
      setProgressMessage("Running Monte Carlo simulations…");
      try {
        const { job_id } = await startSimulation(strength, stage, simMode);
        if (cancelled) return;
        const rankings = await pollSimulation(job_id, (p, message) => {
          if (cancelled) return;
          setProgress(p);
          if (message) setProgressMessage(message);
        });
        if (cancelled) return;
        setPayload(rankings);
        setProgress(1);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Simulation failed");
        }
      } finally {
        if (!cancelled) setSimulating(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [strength, simMode, stage]);

  return {
    teams: payload?.teams ?? [],
    matches,
    groups,
    simulating,
    progress,
    progressMessage,
    error,
  };
}
