"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useDocuments(params?: { folder?: string; status?: string }) {
  const query = useQuery({
    queryKey: ["documents", params],
    queryFn: () => api.listDocuments(params),
    refetchInterval: (q) => {
      const docs = q.state.data?.documents;
      if (docs?.some((d) => d.status === "pending" || d.status === "processing")) {
        return 3000;
      }
      return false;
    },
  });
  return query;
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, folder, tags }: { file: File; folder?: string; tags?: string }) =>
      api.uploadDocument(file, folder, tags),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });
}
