import { ChatWorkspace } from "@/components/ChatWorkspace";

export default function ChatPage() {
  return (
    <div className="flex h-[calc(100vh-11rem)] flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Ask your documents</h1>
        <p className="text-xs text-muted-foreground">
          Watch each agent work in real time, then check the sources behind every answer.
        </p>
      </div>
      <div className="min-h-0 flex-1">
        <ChatWorkspace />
      </div>
    </div>
  );
}
