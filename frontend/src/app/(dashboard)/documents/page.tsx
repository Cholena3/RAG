"use client";
import { DocumentUpload } from "@/components/documents/document-upload";
import { DocumentList } from "@/components/documents/document-list";

export default function DocumentsPage() {
  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Documents</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Upload and manage your documents for Q&A.
        </p>
      </div>
      <DocumentUpload />
      <DocumentList />
    </div>
  );
}
