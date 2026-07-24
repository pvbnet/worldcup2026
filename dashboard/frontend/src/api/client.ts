export type Strength = "elo" | "fifa";

export type Stage =
  | "pre_tournament"
  | "group"
  | "r32"
  | "r16"
  | "qf"
  | "sf"
  | "complete";

export const STAGE_OPTIONS: { id: Stage; label: string }[] = [
  { id: "pre_tournament", label: "Pre-tournament" },
  { id: "group", label: "Group stage done" },
  { id: "r32", label: "Round of 32 done" },
  { id: "r16", label: "Round of 16 done" },
  { id: "qf", label: "Quarterfinals done" },
  { id: "sf", label: "Semifinals done" },
  { id: "complete", label: "Tournament complete" },
];

// Per-stage set of current-year match `stage` values that are fixed/real (as
// opposed to simulated). Mirrors STAGE_INCLUDED_MATCH_STAGES in
// model/src/config.py.
export const STAGE_INCLUDED_MATCH_STAGES: Record<Stage, Set<string>> = {
  pre_tournament: new Set(),
  group: new Set(["group"]),
  r32: new Set(["group", "r32"]),
  r16: new Set(["group", "r32", "r16"]),
  qf: new Set(["group", "r32", "r16", "qf"]),
  sf: new Set(["group", "r32", "r16", "qf", "sf"]),
  complete: new Set(["group", "r32", "r16", "qf", "sf", "final", "third"]),
};

export interface TeamPrediction {
  team: string;
  rank: number;
  model_rank: number;
  elo_rank: number;
  fifa_rank: number;
  active_rank?: number;
  rating: number;
  active_rating?: number;
  p_r32?: number;
  p_r16?: number;
  p_qf?: number;
  p_sf?: number;
  p_final: number;
  p_win: number;
  group?: string | null;
}

export interface RankingsResponse {
  strength: Strength;
  stage?: Stage;
  fifa_snapshot?: string;
  resimulated?: boolean;
  teams: TeamPrediction[];
}

export interface MatchRow {
  year: number;
  date: string;
  team1: string;
  team2: string;
  goals1: number | null;
  goals2: number | null;
  played: boolean;
  group?: string | null;
  stage?: string;
  round?: string;
  et1?: number | null;
  et2?: number | null;
  pen1?: number | null;
  pen2?: number | null;
  advancer?: string | null;
}

export interface SimulationJob {
  job_id: string;
  status: "running" | "done" | "error";
  progress: number;
  message?: string;
  result?: RankingsResponse | null;
}

export async function fetchRankings(
  strength: Strength,
  stage: Stage,
): Promise<RankingsResponse> {
  const params = new URLSearchParams({ strength, stage });
  const res = await fetch(`/api/teams/rankings?${params.toString()}`);
  if (!res.ok) {
    throw new Error("Failed to load rankings");
  }
  return res.json();
}

export async function startSimulation(
  strength: Strength,
  stage: Stage,
  simulations = 1000,
): Promise<{ job_id: string }> {
  const res = await fetch("/api/simulations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strength, stage, simulations }),
  });
  if (!res.ok) {
    throw new Error("Failed to start simulation");
  }
  return res.json();
}

export async function fetchSimulationJob(jobId: string): Promise<SimulationJob> {
  const res = await fetch(`/api/simulations/${jobId}`);
  if (!res.ok) {
    throw new Error("Failed to load simulation status");
  }
  return res.json();
}

export async function pollSimulation(
  jobId: string,
  onProgress: (progress: number, message?: string) => void,
  intervalMs = 300,
): Promise<RankingsResponse> {
  for (;;) {
    const job = await fetchSimulationJob(jobId);
    onProgress(job.progress ?? 0, job.message);
    if (job.status === "done" && job.result) {
      return job.result;
    }
    if (job.status === "error") {
      throw new Error(job.message || "Simulation failed");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export async function fetchMatches(year = 2026): Promise<MatchRow[]> {
  const res = await fetch(`/api/matches?year=${year}`);
  const data = await res.json();
  return data.matches ?? [];
}

export async function fetchGroups(): Promise<Record<string, unknown[]>> {
  const res = await fetch("/api/groups?year=2026");
  const data = await res.json();
  return data.groups ?? {};
}

export async function refreshData(): Promise<void> {
  await fetch("/api/refresh-data", { method: "POST" });
}
