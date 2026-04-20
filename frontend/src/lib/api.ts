const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${API_URL}${path}`, { ...options, headers });

    if (res.status === 401) {
      const refreshed = await this.tryRefresh();
      if (refreshed) return this.request<T>(path, options);
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const message = typeof err.detail === "string"
        ? err.detail
        : Array.isArray(err.detail)
          ? err.detail.map((e: any) => e.msg || e).join(", ")
          : "Request failed";
      throw new Error(message);
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  private async tryRefresh(): Promise<boolean> {
    const refresh = typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null;
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      return true;
    } catch {
      return false;
    }
  }

  // Auth
  register(email: string, password: string, full_name?: string) {
    return this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    });
  }

  async login(email: string, password: string) {
    const data: any = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data;
  }

  logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }

  getMe() {
    return this.request<import("@/types").User>("/auth/me");
  }

  updateProfile(data: { full_name?: string; avatar_url?: string }) {
    return this.request<import("@/types").User>("/auth/me", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  changePassword(currentPassword: string, newPassword: string) {
    return this.request("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  }

  verifyEmail(token: string) {
    return this.request(`/auth/verify-email?token=${token}`, { method: "POST" });
  }

  // 2FA
  enable2FA() {
    return this.request<import("@/types").Enable2FAResponse>("/auth/2fa/enable", { method: "POST" });
  }

  verify2FA(totpCode: string, secret: string) {
    return this.request(`/auth/2fa/verify?secret=${secret}`, {
      method: "POST",
      body: JSON.stringify({ totp_code: totpCode }),
    });
  }

  disable2FA(totpCode: string) {
    return this.request("/auth/2fa/disable", {
      method: "POST",
      body: JSON.stringify({ totp_code: totpCode }),
    });
  }

  // Sessions
  listSessions() {
    return this.request<import("@/types").Session[]>("/auth/sessions");
  }

  revokeSession(sessionId: string) {
    return this.request(`/auth/sessions/${sessionId}`, { method: "DELETE" });
  }

  revokeAllSessions() {
    return this.request("/auth/sessions", { method: "DELETE" });
  }

  // Audit logs
  getAuditLogs(skip = 0, limit = 50) {
    return this.request<import("@/types").AuditLog[]>(`/auth/audit-logs?skip=${skip}&limit=${limit}`);
  }

  // Account deletion
  deleteAccount(password: string) {
    return this.request("/auth/account", {
      method: "DELETE",
      body: JSON.stringify({ password, confirmation: "DELETE" }),
    });
  }

  // API Keys
  createApiKey(name: string) {
    return this.request<import("@/types").APIKey>("/auth/api-keys", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  listApiKeys() {
    return this.request<import("@/types").APIKey[]>("/auth/api-keys");
  }

  deleteApiKey(keyId: string) {
    return this.request(`/auth/api-keys/${keyId}`, { method: "DELETE" });
  }

  // Documents
  uploadDocument(file: File, folder?: string, tags?: string) {
    const form = new FormData();
    form.append("file", file);
    if (folder) form.append("folder", folder);
    if (tags) form.append("tags", tags);
    return this.request<import("@/types").Document>("/documents/upload", {
      method: "POST",
      body: form,
    });
  }

  listDocuments(params?: { folder?: string; status?: string; skip?: number; limit?: number }) {
    const q = new URLSearchParams();
    if (params?.folder) q.set("folder", params.folder);
    if (params?.status) q.set("status", params.status);
    if (params?.skip) q.set("skip", String(params.skip));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return this.request<import("@/types").DocumentListResponse>(`/documents${qs ? `?${qs}` : ""}`);
  }

  deleteDocument(id: string) {
    return this.request(`/documents/${id}`, { method: "DELETE" });
  }

  getDocumentStatus(id: string) {
    return this.request<{ document_id: string; status: string; chunk_count: number; error_message: string | null }>(
      `/documents/${id}/status`
    );
  }

  // Chat
  chat(query: string, conversationId?: string, documentIds?: string[], model?: string) {
    return this.request<import("@/types").ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        query,
        conversation_id: conversationId,
        document_ids: documentIds,
        model,
      }),
    });
  }

  chatStream(query: string, conversationId?: string, documentIds?: string[], model?: string) {
    const token = this.getToken();
    return fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        query,
        conversation_id: conversationId,
        document_ids: documentIds,
        model,
      }),
    });
  }

  listConversations(skip = 0, limit = 20) {
    return this.request<import("@/types").ConversationListResponse>(
      `/chat/history?skip=${skip}&limit=${limit}`
    );
  }

  getConversation(id: string) {
    return this.request<import("@/types").Conversation>(`/chat/history/${id}`);
  }

  deleteConversation(id: string) {
    return this.request(`/chat/history/${id}`, { method: "DELETE" });
  }

  submitFeedback(messageId: string, feedback: number) {
    return this.request("/chat/feedback", {
      method: "POST",
      body: JSON.stringify({ message_id: messageId, feedback }),
    });
  }

  // Admin
  getStats() {
    return this.request<import("@/types").AdminStats>("/admin/stats");
  }

  listUsers() {
    return this.request<any[]>("/admin/users");
  }

  listModels() {
    return this.request<any[]>("/admin/models");
  }

  // Preferences
  getPreferences() {
    return this.request<Record<string, any>>("/preferences");
  }

  updatePreferences(prefs: Record<string, any>) {
    return this.request("/preferences", {
      method: "PUT",
      body: JSON.stringify(prefs),
    });
  }

  listAvailableModels() {
    return this.request<any[]>("/preferences/models");
  }

  // Admin defaults
  getGlobalDefaults() {
    return this.request<Record<string, any>>("/admin/defaults");
  }

  updateGlobalDefaults(defaults: Record<string, any>) {
    return this.request("/admin/defaults", {
      method: "PUT",
      body: JSON.stringify(defaults),
    });
  }
}

export const api = new ApiClient();
