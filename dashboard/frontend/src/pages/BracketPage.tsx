import { Bracket } from "../components/Bracket";
import { MatchRow } from "../api/client";

export function BracketPage({ matches }: { matches: MatchRow[] }) {
  return (
    <section className="bracket-page">
      <div className="panel bracket-page-intro">
        <h2>Knockout bracket</h2>
        <p>
          Actual 2026 World Cup fixtures and results from Round of 32 through
          the Final (including third place).
        </p>
      </div>
      <Bracket matches={matches} />
    </section>
  );
}
