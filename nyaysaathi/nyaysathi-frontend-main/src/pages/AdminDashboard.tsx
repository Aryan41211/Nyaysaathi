import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { clearSession } from "@/lib/auth";
import {
  createWorkflow,
  deleteWorkflow,
  fetchAdminQueries,
  fetchAdminUsers,
  updateWorkflow,
  type AdminQueriesResponse,
  type AdminUsersResponse,
} from "@/lib/api";
import { useNavigate } from "react-router-dom";

type Tab = "users" | "queries" | "workflows";

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState<Tab>("users");
  const [usersData, setUsersData] = useState<AdminUsersResponse | null>(null);
  const [queriesData, setQueriesData] = useState<AdminQueriesResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [workflowId, setWorkflowId] = useState("");
  const [workflowPayload, setWorkflowPayload] = useState("{}");
  const [workflowUpdates, setWorkflowUpdates] = useState("{}");
  const navigate = useNavigate();

  const stats = useMemo(
    () => ({
      totalUsers: usersData?.total_users ?? 0,
      totalQueries: queriesData?.total_queries ?? 0,
    }),
    [usersData, queriesData],
  );

  const loadAdminData = async () => {
    setLoading(true);
    setError("");
    try {
      const [users, queries] = await Promise.all([fetchAdminUsers(), fetchAdminQueries()]);
      setUsersData(users);
      setQueriesData(queries);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load admin data";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAdminData();
  }, []);

  const parseJson = (raw: string): Record<string, unknown> => {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (Array.isArray(parsed) || parsed === null) {
      throw new Error("Payload must be a JSON object");
    }
    return parsed;
  };

  const onCreateWorkflow = async () => {
    try {
      const payload = parseJson(workflowPayload);
      await createWorkflow({ payload });
      setError("");
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workflow");
    }
  };

  const onUpdateWorkflow = async () => {
    try {
      if (!workflowId.trim()) throw new Error("Workflow ID is required");
      const updates = parseJson(workflowUpdates);
      await updateWorkflow({ workflow_id: workflowId.trim(), updates });
      setError("");
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update workflow");
    }
  };

  const onDeleteWorkflow = async () => {
    try {
      if (!workflowId.trim()) throw new Error("Workflow ID is required");
      await deleteWorkflow({ workflow_id: workflowId.trim() });
      setError("");
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete workflow");
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="grid md:grid-cols-[220px_1fr] min-h-screen">
        <aside className="border-r bg-card p-6 space-y-6">
          <div>
            <h1 className="text-xl font-semibold">Admin Panel</h1>
            <p className="text-sm text-muted-foreground">NyaySaathi</p>
          </div>

          <nav className="space-y-2">
            <button className="w-full text-left px-3 py-2 rounded-md hover:bg-accent" onClick={() => setActiveTab("users")}>Users</button>
            <button className="w-full text-left px-3 py-2 rounded-md hover:bg-accent" onClick={() => setActiveTab("queries")}>Queries</button>
            <button className="w-full text-left px-3 py-2 rounded-md hover:bg-accent" onClick={() => setActiveTab("workflows")}>Workflows</button>
          </nav>

          <Button
            variant="destructive"
            onClick={() => {
              clearSession();
              navigate("/login");
            }}
          >
            Sign Out
          </Button>
        </aside>

        <main className="p-6 md:p-10 space-y-6">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="rounded-lg border p-4 bg-card">
              <p className="text-sm text-muted-foreground">Total Users</p>
              <p className="text-2xl font-semibold">{stats.totalUsers}</p>
            </div>
            <div className="rounded-lg border p-4 bg-card">
              <p className="text-sm text-muted-foreground">Total Queries</p>
              <p className="text-2xl font-semibold">{stats.totalQueries}</p>
            </div>
          </div>

          {error ? <div className="text-sm text-red-600">{error}</div> : null}
          {loading ? <div className="text-sm text-muted-foreground">Loading...</div> : null}

          {activeTab === "users" && (
            <div className="rounded-lg border bg-card overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3">Name</th>
                    <th className="text-left p-3">Email</th>
                    <th className="text-left p-3">Role</th>
                    <th className="text-left p-3">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {(usersData?.users ?? []).map((u) => (
                    <tr key={u.id} className="border-t">
                      <td className="p-3">{u.name}</td>
                      <td className="p-3">{u.email}</td>
                      <td className="p-3">{u.role}</td>
                      <td className="p-3">{new Date(u.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "queries" && (
            <div className="rounded-lg border bg-card overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3">User</th>
                    <th className="text-left p-3">Query</th>
                    <th className="text-left p-3">Category</th>
                    <th className="text-left p-3">Subcategory</th>
                    <th className="text-left p-3">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {(queriesData?.queries ?? []).map((q) => (
                    <tr key={q.id} className="border-t align-top">
                      <td className="p-3">{q.user_email || q.user_id}</td>
                      <td className="p-3">{q.query_text}</td>
                      <td className="p-3">{q.category}</td>
                      <td className="p-3">{q.subcategory}</td>
                      <td className="p-3">{new Date(q.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "workflows" && (
            <div className="rounded-lg border bg-card p-6 space-y-4">
              <h2 className="text-lg font-semibold">Workflow Management</h2>
              <Input placeholder="Workflow ID (for update/delete)" value={workflowId} onChange={(e) => setWorkflowId(e.target.value)} />
              <label className="text-sm font-medium">Create Payload (JSON)</label>
              <textarea
                className="w-full min-h-[120px] rounded-md border bg-background p-3 text-sm"
                value={workflowPayload}
                onChange={(e) => setWorkflowPayload(e.target.value)}
              />

              <label className="text-sm font-medium">Update Payload (JSON)</label>
              <textarea
                className="w-full min-h-[120px] rounded-md border bg-background p-3 text-sm"
                value={workflowUpdates}
                onChange={(e) => setWorkflowUpdates(e.target.value)}
              />

              <div className="flex flex-wrap gap-3">
                <Button onClick={onCreateWorkflow}>Add Workflow</Button>
                <Button variant="secondary" onClick={onUpdateWorkflow}>Edit Workflow</Button>
                <Button variant="destructive" onClick={onDeleteWorkflow}>Delete Workflow</Button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;
