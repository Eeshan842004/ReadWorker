import { PipelineExplainer } from "@/components/PipelineExplainer";

export default function TracesPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Agent pipeline</h1>
        <p className="max-w-2xl text-xs leading-relaxed text-muted-foreground">
          In Multi-agent mode every answer streams a live trace: each node reports the moment it
          finishes, so you can watch the pipeline execute. Below is the shape of that pipeline —
          press play to replay a run.
        </p>
      </div>
      <PipelineExplainer />
    </div>
  );
}
