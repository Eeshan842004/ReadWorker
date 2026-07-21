"use client";

import { useState } from "react";

import { DocumentList } from "@/components/DocumentList";
import { DocumentUpload } from "@/components/DocumentUpload";

export function UploadPanel() {
  // Bumping this remounts the list so it re-fetches after each successful upload.
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      <DocumentUpload onUploaded={() => setRefreshKey((k) => k + 1)} />

      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold">Your uploaded documents</h2>
          <span className="h-px flex-1 bg-border" />
        </div>
        <DocumentList key={refreshKey} />
      </div>
    </div>
  );
}
