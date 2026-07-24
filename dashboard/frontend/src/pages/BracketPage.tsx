import { Bracket } from "../components/Bracket";
import { MatchRow, Stage } from "../api/client";

export function BracketPage({
  matches,
  stage,
}: {
  matches: MatchRow[];
  stage: Stage;
}) {
  return (
    <section className="bracket-page">
      <div className="panel bracket-page-intro">
        <h2>Knockout bracket</h2>
        <p>
          Actual 2026 World Cup fixtures and results from Round of 32 through
          the Final (including third place), masked to what would have been
          knowable at the selected tournament stage.
        </p>
      </div>
      <Bracket matches={matches} stage={stage} />
    </section>
  );
}
