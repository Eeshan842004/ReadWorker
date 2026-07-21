import { EvalDashboard } from "@/components/EvalDashboard";

export default function EvalPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Evaluation</h1>
        <p className="text-xs text-muted-foreground">
          Retrieval and answer quality, measured — not vibes.
        </p>
      </div>
      <EvalDashboard />
    </div>
  );
}
