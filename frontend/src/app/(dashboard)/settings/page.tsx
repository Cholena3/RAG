"use client";
import { useState, useEffect } from "react";
import { Key, Plus, Loader2, Sliders, Save, Shield, Monitor, Trash2, AlertTriangle, History, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import type { APIKey, Session, AuditLog, Enable2FAResponse } from "@/types";
import { formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const { user, fetchUser } = useAuthStore();
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Profile
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || "");
  const [savingProfile, setSavingProfile] = useState(false);

  // Password
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  // 2FA
  const [twoFAData, setTwoFAData] = useState<Enable2FAResponse | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [disableTotpCode, setDisableTotpCode] = useState("");
  const [enabling2FA, setEnabling2FA] = useState(false);

  // Sessions
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  // Audit logs
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Delete account
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);

  // Preferences
  const [models, setModels] = useState<any[]>([]);
  const [prefs, setPrefs] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.listApiKeys().then(setApiKeys).catch(() => {});
    api.getPreferences().then(setPrefs).catch(() => {});
    api.listAvailableModels().then(setModels).catch(() => {});
    api.listSessions().then(setSessions).catch(() => {});
  }, []);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setAvatarUrl(user.avatar_url || "");
    }
  }, [user]);

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    setLoading(true);
    try {
      const key = await api.createApiKey(newKeyName);
      setCreatedKey(key.key || null);
      setApiKeys((prev) => [key, ...prev]);
      setNewKeyName("");
    } catch { /* ignore */ }
    setLoading(false);
  };

  const deleteKey = async (keyId: string) => {
    try {
      await api.deleteApiKey(keyId);
      setApiKeys((prev) => prev.filter((k) => k.id !== keyId));
    } catch { /* ignore */ }
  };

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      await api.updateProfile({ full_name: fullName, avatar_url: avatarUrl || undefined });
      await fetchUser();
    } catch { /* ignore */ }
    setSavingProfile(false);
  };

  const changePassword = async () => {
    setPasswordError("");
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match");
      return;
    }
    setChangingPassword(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      alert("Password changed successfully");
    } catch (e: any) {
      setPasswordError(e.message || "Failed to change password");
    }
    setChangingPassword(false);
  };

  const startEnable2FA = async () => {
    try {
      const data = await api.enable2FA();
      setTwoFAData(data);
    } catch { /* ignore */ }
  };

  const confirmEnable2FA = async () => {
    if (!twoFAData || !totpCode) return;
    setEnabling2FA(true);
    try {
      await api.verify2FA(totpCode, twoFAData.secret);
      setTwoFAData(null);
      setTotpCode("");
      await fetchUser();
    } catch { /* ignore */ }
    setEnabling2FA(false);
  };

  const disable2FA = async () => {
    if (!disableTotpCode) return;
    try {
      await api.disable2FA(disableTotpCode);
      setDisableTotpCode("");
      await fetchUser();
    } catch { /* ignore */ }
  };

  const loadSessions = async () => {
    setLoadingSessions(true);
    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch { /* ignore */ }
    setLoadingSessions(false);
  };

  const revokeSession = async (sessionId: string) => {
    try {
      await api.revokeSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch { /* ignore */ }
  };

  const revokeAllSessions = async () => {
    if (!confirm("This will log you out of all devices. Continue?")) return;
    try {
      await api.revokeAllSessions();
      setSessions([]);
    } catch { /* ignore */ }
  };

  const loadAuditLogs = async () => {
    setLoadingLogs(true);
    try {
      const data = await api.getAuditLogs();
      setAuditLogs(data);
    } catch { /* ignore */ }
    setLoadingLogs(false);
  };

  const deleteAccount = async () => {
    if (deleteConfirm !== "DELETE") {
      alert("Please type DELETE to confirm");
      return;
    }
    setDeleting(true);
    try {
      await api.deleteAccount(deletePassword);
      api.logout();
      window.location.href = "/login";
    } catch (e: any) {
      alert(e.message || "Failed to delete account");
    }
    setDeleting(false);
  };

  const savePrefs = async () => {
    setSaving(true);
    try {
      await api.updatePreferences(prefs);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* ignore */ }
    setSaving(false);
  };

  return (
    <div className="h-full overflow-auto p-6 space-y-6 max-w-2xl">
      <h1 className="text-2xl font-semibold">Settings</h1>

      {/* Profile Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <UserIcon className="h-5 w-5" /> Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">Email</label>
            <Input id="email" value={user?.email || ""} disabled />
            {user && !user.email_verified && (
              <p className="text-xs text-yellow-600">Email not verified. Check your inbox.</p>
            )}
          </div>
          <div className="space-y-2">
            <label htmlFor="fullName" className="text-sm font-medium">Full Name</label>
            <Input
              id="fullName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="avatarUrl" className="text-sm font-medium">Avatar URL</label>
            <Input
              id="avatarUrl"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              placeholder="https://example.com/avatar.jpg"
            />
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">{user?.role}</Badge>
            {user?.has_2fa && <Badge variant="success">2FA Enabled</Badge>}
          </div>
          <Button onClick={saveProfile} disabled={savingProfile}>
            {savingProfile ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            Save Profile
          </Button>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Change Password</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            type="password"
            placeholder="Current password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
          <Input
            type="password"
            placeholder="New password (min 8 chars, uppercase, lowercase, digit)"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <Input
            type="password"
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          {passwordError && <p className="text-sm text-red-500">{passwordError}</p>}
          <Button onClick={changePassword} disabled={changingPassword || !currentPassword || !newPassword}>
            {changingPassword ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Change Password
          </Button>
        </CardContent>
      </Card>

      {/* 2FA */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" /> Two-Factor Authentication
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {user?.has_2fa ? (
            <div className="space-y-4">
              <p className="text-sm text-green-600">2FA is enabled on your account.</p>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter TOTP code to disable"
                  value={disableTotpCode}
                  onChange={(e) => setDisableTotpCode(e.target.value)}
                />
                <Button variant="destructive" onClick={disable2FA} disabled={!disableTotpCode}>
                  Disable 2FA
                </Button>
              </div>
            </div>
          ) : twoFAData ? (
            <div className="space-y-4">
              <p className="text-sm">Scan this QR code with your authenticator app:</p>
              <div className="bg-white p-4 rounded-lg inline-block">
                <img src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(twoFAData.qr_uri)}`} alt="2FA QR Code" />
              </div>
              <p className="text-xs text-muted-foreground">Or enter manually: {twoFAData.secret}</p>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter 6-digit code"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  maxLength={6}
                />
                <Button onClick={confirmEnable2FA} disabled={enabling2FA || totpCode.length !== 6}>
                  {enabling2FA ? <Loader2 className="h-4 w-4 animate-spin" /> : "Verify"}
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={startEnable2FA}>Enable 2FA</Button>
          )}
        </CardContent>
      </Card>

      {/* Sessions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Monitor className="h-5 w-5" /> Active Sessions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button variant="outline" onClick={loadSessions} disabled={loadingSessions}>
              {loadingSessions ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Load Sessions
            </Button>
            {sessions.length > 0 && (
              <Button variant="destructive" onClick={revokeAllSessions}>
                Revoke All
              </Button>
            )}
          </div>
          <div className="space-y-2">
            {sessions.map((s) => (
              <div key={s.id} className="flex items-center justify-between p-3 border rounded-lg text-sm">
                <div>
                  <p className="font-medium">{s.device_info || "Unknown device"}</p>
                  <p className="text-xs text-muted-foreground">
                    IP: {s.ip_address || "Unknown"} · Last used: {formatDate(s.last_used_at)}
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => revokeSession(s.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Audit Logs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="h-5 w-5" /> Activity Log
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button variant="outline" onClick={loadAuditLogs} disabled={loadingLogs}>
            {loadingLogs ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Load Activity
          </Button>
          <div className="space-y-2 max-h-64 overflow-auto">
            {auditLogs.map((log) => (
              <div key={log.id} className="p-2 border rounded text-xs">
                <span className="font-medium">{log.action}</span>
                <span className="text-muted-foreground ml-2">{formatDate(log.created_at)}</span>
                {log.ip_address && <span className="text-muted-foreground ml-2">from {log.ip_address}</span>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Model & RAG Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Sliders className="h-5 w-5" /> Model &amp; RAG Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="model" className="text-sm font-medium">LLM Model</label>
            <select
              id="model"
              value={prefs.model || ""}
              onChange={(e) => setPrefs({ ...prefs, model: e.target.value })}
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
              <label htmlFor="temperature" className="text-sm font-medium">Temperature</label>
              <Input
                id="temperature"
                type="number"
                min={0} max={2} step={0.1}
                value={prefs.temperature ?? 0.7}
                onChange={(e) => setPrefs({ ...prefs, temperature: parseFloat(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="top_k" className="text-sm font-medium">Top-K Retrieval</label>
              <Input
                id="top_k"
                type="number"
                min={1} max={20}
                value={prefs.top_k ?? 5}
                onChange={(e) => setPrefs({ ...prefs, top_k: parseInt(e.target.value) })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="chunk_size" className="text-sm font-medium">Chunk Size</label>
              <Input
                id="chunk_size"
                type="number"
                min={100} max={4000} step={50}
                value={prefs.chunk_size ?? 512}
                onChange={(e) => setPrefs({ ...prefs, chunk_size: parseInt(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="max_tokens" className="text-sm font-medium">Max Tokens</label>
              <Input
                id="max_tokens"
                type="number"
                min={256} max={8192} step={256}
                value={prefs.max_tokens ?? 2048}
                onChange={(e) => setPrefs({ ...prefs, max_tokens: parseInt(e.target.value) })}
              />
            </div>
          </div>
          <Button onClick={savePrefs} disabled={saving} className="gap-2">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {saved ? "Saved" : "Save Preferences"}
          </Button>
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Key className="h-5 w-5" /> API Keys
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Key name"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              aria-label="API key name"
            />
            <Button onClick={createKey} disabled={loading || !newKeyName.trim()}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />}
              Create
            </Button>
          </div>
          {createdKey && (
            <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-3 text-sm">
              <p className="font-medium text-green-800 dark:text-green-200">Key created — copy it now:</p>
              <code className="block mt-1 break-all text-xs">{createdKey}</code>
            </div>
          )}
          <div className="space-y-2">
            {apiKeys.map((k) => (
              <div key={k.id} className="flex items-center justify-between p-3 border rounded-lg text-sm">
                <div>
                  <p className="font-medium">{k.name}</p>
                  <p className="text-xs text-muted-foreground">{k.prefix}... · Created {formatDate(k.created_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={k.is_active ? "success" : "secondary"}>
                    {k.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Button variant="ghost" size="sm" onClick={() => deleteKey(k.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Delete Account */}
      <Card className="border-red-200 dark:border-red-900">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" /> Danger Zone
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>
          <Input
            type="password"
            placeholder="Enter your password"
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
          />
          <Input
            placeholder="Type DELETE to confirm"
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
          />
          <Button
            variant="destructive"
            onClick={deleteAccount}
            disabled={deleting || !deletePassword || deleteConfirm !== "DELETE"}
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
            Delete My Account
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
