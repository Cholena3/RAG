"use client";
import { useState, useEffect } from "react";
import { Users, FileText, MessageSquare, ThumbsUp, ThumbsDown, Cpu, Loader2, Save, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import type { AdminStats } from "@/types";
import { formatDate } from "@/lib/utils";

export default function AdminPage() {
  const { user } = useAuthStore();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [defaults, setDefaults] = useState<Record<string, any>>({});
  const [savingDefaults, setSavingDefaults] = useState(false);
  const [defaultsSaved, setDefaultsSaved] = useState(false);

  useEffect(() => {
    if (user?.role !== "admin") return;
    Promise.all([api.getStats(), api.listUsers(), api.listModels(), api.getGlobalDefaults()])
      .then(([s, u, m, d]) => {
        setStats(s);
        setUsers(u);
        setModels(m);
        setDefaults(d);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  const saveDefaults = async () => {
    setSavingDefaults(true);
    try {
      await api.updateGlobalDefaults(defaults);
      setDefaultsSaved(true);
      setTimeout(() => setDefaultsSaved(false), 2000);
    } catch { /* ignore */ }
    setSavingDefaults(false);
  };

  if (user?.role !== "admin") {
    return <div className="p-6 text-muted-foreground">Admin access required.</div>;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Admin Dashboard</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Users", value: stats.users, icon: Users },
            { label: "Documents", value: stats.documents, icon: FileText },
            { label: "Conversations", value: stats.conversations, icon: MessageSquare },
            { label: "Messages", value: stats.messages, icon: MessageSquare },
          ].map((s) => (
            <Card key={s.label}>
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <s.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{s.value}</p>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {stats && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Feedback</CardTitle></CardHeader>
          <CardContent className="flex gap-6">
            <div className="flex items-center gap-2">
              <ThumbsUp className="h-5 w-5 text-green-600" />
              <span className="text-lg font-semibold">{stats.feedback.positive}</span>
              <span className="text-sm text-muted-foreground">positive</span>
            </div>
            <div className="flex items-center gap-2">
              <ThumbsDown className="h-5 w-5 text-red-600" />
              <span className="text-lg font-semibold">{stats.feedback.negative}</span>
              <span className="text-sm text-muted-foreground">negative</span>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-lg">Users</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {users.map((u) => (
              <div key={u.id} className="flex items-center justify-between p-3 border rounded-lg text-sm">
                <div>
                  <p className="font-medium">{u.email}</p>
                  <p className="text-xs text-muted-foreground">{u.full_name || "—"} · Joined {formatDate(u.created_at)}</p>
                </div>
                <div className="flex gap-2">
                  <Badge variant={u.role === "admin" ? "default" : "secondary"}>{u.role}</Badge>
                  <Badge variant={u.is_active ? "success" : "destructive"}>
                    {u.is_active ? "Active" : "Disabled"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Cpu className="h-5 w-5" /> Available Models
          </CardTitle>
        </CardHeader>
        <CardContent>
          {models.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No models found. Make sure Ollama is running and has models pulled.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {models.map((m: any) => (
                <div key={m.name} className="p-3 border rounded-lg text-sm">
                  <p className="font-medium">{m.name}</p>
                  {m.size && (
                    <p className="text-xs text-muted-foreground">
                      {(m.size / 1e9).toFixed(1)} GB
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Settings className="h-5 w-5" /> Global Defaults
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            These defaults apply to all users unless they override them in their own settings.
          </p>

          <div className="space-y-2">
            <label htmlFor="default-model" className="text-sm font-medium">Default LLM Model</label>
            <select
              id="default-model"
              value={defaults.model || ""}
              onChange={(e) => setDefaults({ ...defaults, model: e.target.value })}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            >
              {models.length === 0 && <option value="">No models available</option>}
              {models.map((m: any) => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label htmlFor="default-embed" className="text-sm font-medium">Default Embedding Model</label>
            <select
              id="default-embed"
              value={defaults.embedding_model || ""}
              onChange={(e) => setDefaults({ ...defaults, embedding_model: e.target.value })}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            >
              {models.length === 0 && <option value="">No models available</option>}
              {models.map((m: any) => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="def-temp" className="text-sm font-medium">Temperature</label>
              <Input id="def-temp" type="number" min={0} max={2} step={0.1}
                value={defaults.temperature ?? 0.7}
                onChange={(e) => setDefaults({ ...defaults, temperature: parseFloat(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="def-topk" className="text-sm font-medium">Top-K</label>
              <Input id="def-topk" type="number" min={1} max={20}
                value={defaults.top_k ?? 5}
                onChange={(e) => setDefaults({ ...defaults, top_k: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <label htmlFor="def-chunk" className="text-sm font-medium">Chunk Size</label>
              <Input id="def-chunk" type="number" min={100} max={4000} step={50}
                value={defaults.chunk_size ?? 512}
                onChange={(e) => setDefaults({ ...defaults, chunk_size: parseInt(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="def-overlap" className="text-sm font-medium">Chunk Overlap</label>
              <Input id="def-overlap" type="number" min={0} max={500} step={10}
                value={defaults.chunk_overlap ?? 50}
                onChange={(e) => setDefaults({ ...defaults, chunk_overlap: parseInt(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="def-maxtok" className="text-sm font-medium">Max Tokens</label>
              <Input id="def-maxtok" type="number" min={256} max={8192} step={256}
                value={defaults.max_tokens ?? 2048}
                onChange={(e) => setDefaults({ ...defaults, max_tokens: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <Button onClick={saveDefaults} disabled={savingDefaults} className="gap-2">
            {savingDefaults ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {defaultsSaved ? "Saved" : "Save Global Defaults"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
