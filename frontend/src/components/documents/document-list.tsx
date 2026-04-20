"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Trash2, Eye, Clock, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useDocuments, useDeleteDocument } from "@/hooks/use-documents";
import { formatBytes, formatDate } from "@/lib/utils";
import { DocumentPreview } from "./document-preview";
import type { Document } from "@/types";

const statusConfig = {
  pending: { icon: Clock, variant: "warning" as const, label: "Pending" },
  processing: { icon: Loader2, variant: "secondary" as const, label: "Processing" },
  ready: { icon: CheckCircle, variant: "success" as const, label: "Ready" },
  failed: { icon: AlertCircle, variant: "destructive" as const, label: "Failed" },
};

export function DocumentList() {
  const { data, isLoading } = useDocuments();
  const deleteMutation = useDeleteDocument();
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data?.documents?.length) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>No documents yet. Upload some to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.documents.map((doc, i) => {
        const status = statusConfig[doc.status] || statusConfig.pending;
        const StatusIcon = status.icon;
        return (
          <motion.div
            key={doc.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-center gap-4 p-4 rounded-lg border hover:bg-accent/50 transition-colors"
          >
            <FileText className="h-8 w-8 text-primary shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{doc.filename}</p>
              <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                <span>{formatBytes(doc.file_size)}</span>
                {doc.page_count && <span>{doc.page_count} pages</span>}
                {doc.chunk_count > 0 && <span>{doc.chunk_count} chunks</span>}
                <span>{formatDate(doc.created_at)}</span>
              </div>
              {doc.tags.length > 0 && (
                <div className="flex gap-1 mt-1.5">
                  {doc.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                  ))}
                </div>
              )}
            </div>
            <Badge variant={status.variant} className="gap-1 shrink-0">
              <StatusIcon className={`h-3 w-3 ${doc.status === "processing" ? "animate-spin" : ""}`} />
              {status.label}
            </Badge>
            {doc.status === "ready" && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setPreviewDoc(doc)}
                aria-label={`Preview ${doc.filename}`}
              >
                <Eye className="h-4 w-4 text-muted-foreground" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => deleteMutation.mutate(doc.id)}
              disabled={deleteMutation.isPending}
              aria-label={`Delete ${doc.filename}`}
            >
              <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
            </Button>
          </motion.div>
        );
      })}
      {previewDoc && (
        <DocumentPreview document={previewDoc} onClose={() => setPreviewDoc(null)} />
      )}
    </div>
  );
}
