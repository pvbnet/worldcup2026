import { useCallback, useEffect, useState } from "react";
import {
  fetchGroups,
  fetchMatches,
  pollSimulation,
  refreshData,
  startSimulation,
  MatchRow,
  RankingsResponse,
  Stage,
  Strength,
} from "../api/client";

export function useDashboard(strength: Strength, simulations: number, stage: Stage) {
  const [payload, setPayload] = useState<RankingsResponse | null>(null);
  const [matches, setMatches] = useState<MatchRow[]>([]);
  const [groups, setGroups] = useState<Record<string, unknown[]>>({});
  const [simulating, setSimulating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [staticLoaded, setStaticLoaded] = useState(false);

  const loadStatic = useCallback(async () => {
    const [matchRows, groupRows] = await Promise.all([
      fetchMatches(2026),
      fetchGroups(),
    ]);
    setMatches(matchRows);
    setGroups(groupRows);
    setStaticLoaded(true);
  }, []);

  const runSimulations = useCallback(
    async (source: Strength, n: number, forStage: Stage) => {
      setSimulating(true);
      setProgress(0);
      setProgressMessage("Running Monte Carlo simulations…");
      setError(null);
      try {
        const { job_id } = await startSimulation(source, forStage, n);
        const rankings = await pollSimulation(job_id, (p, message) => {
          setProgress(p);
          if (message) setProgressMessage(message);
        });
        setPayload(rankings);
        setProgress(1);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Simulation failed");
      } finally {
        setSimulating(false);
      }
    },
    [],
  );

  useEffect(() => {
    loadStatic().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load matches");
    });
  }, [loadStatic]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setSimulating(true);
      setProgress(0);
      setProgressMessage("Running Monte Carlo simulations…");
      setError(null);
      try {
        const { job_id } = await startSimulation(strength, stage, simulations);
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
  }, [strength, simulations, stage]);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      await refreshData();
      await loadStatic();
      await runSimulations(strength, simulations, stage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    }
  }, [loadStatic, runSimulations, strength, simulations, stage]);

  return {
    teams: payload?.teams ?? [],
    meta: payload,
    matches,
    groups,
    loading: !staticLoaded && !payload,
    simulating,
    progress,
    progressMessage,
    error,
    refresh,
  };
}
