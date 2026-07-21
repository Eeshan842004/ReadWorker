import { DocumentList } from "@/components/DocumentList";

export default function DocumentsPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Documents</h1>
        <p className="text-xs text-muted-foreground">
          Everything in your knowledge base. New uploads add to it — nothing is overwritten.
        </p>
      </div>
      <DocumentList />
    </div>
  );
}
