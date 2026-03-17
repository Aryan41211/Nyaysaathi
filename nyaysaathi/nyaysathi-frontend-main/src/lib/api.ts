import { AuthSession, getSession, UserRole } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8010";

interface SignupPayload {
  name: string;
  email: string;
  password: string;
}

interface LoginPayload {
  email: string;
  password: string;
  login_as: UserRole;
}

interface WorkflowCreatePayload {
  payload: Record<string, unknown>;
}

interface WorkflowUpdatePayload {
  workflow_id: string;
  updates: Record<string, unknown>;
}

interface WorkflowDeletePayload {
  workflow_id: string;
}

interface ClassifyPayload {
  user_input: string;
  user_id?: string;
}

async function request<T>(path: string, init: RequestInit = {}, withAuth = false): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  headers.set("Content-Type", "application/json");

  if (withAuth) {
    const session = getSession();
    if (session?.access_token) {
      headers.set("Authorization", `Bearer ${session.access_token}`);
    }
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}

export function signup(payload: SignupPayload): Promise<AuthSession> {
  return request<AuthSession>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: LoginPayload): Promise<AuthSession> {
  return request<AuthSession>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface AdminUsersResponse {
  total_users: number;
  users: Array<{ id: string; name: string; email: string; role: UserRole; created_at: string }>;
}

export interface AdminQueriesResponse {
  total_queries: number;
  queries: Array<{
    id: string;
    user_id: string;
    user_email: string;
    query_text: string;
    category: string;
    subcategory: string;
    created_at: string;
  }>;
}

export function fetchAdminUsers(): Promise<AdminUsersResponse> {
  return request<AdminUsersResponse>("/admin/users", { method: "GET" }, true);
}

export function fetchAdminQueries(): Promise<AdminQueriesResponse> {
  return request<AdminQueriesResponse>("/admin/queries", { method: "GET" }, true);
}

export function createWorkflow(payload: WorkflowCreatePayload): Promise<{ workflow_id: string }> {
  return request<{ workflow_id: string }>("/admin/workflows", {
    method: "POST",
    body: JSON.stringify(payload),
  }, true);
}

export function updateWorkflow(payload: WorkflowUpdatePayload): Promise<{ status: string }> {
  return request<{ status: string }>("/admin/workflows", {
    method: "PUT",
    body: JSON.stringify(payload),
  }, true);
}

export function deleteWorkflow(payload: WorkflowDeletePayload): Promise<{ status: string }> {
  return request<{ status: string }>("/admin/workflows", {
    method: "DELETE",
    body: JSON.stringify(payload),
  }, true);
}

export interface ClassifyResponse {
  category: string;
  subcategory: string;
  confidence: number;
  intent_summary: string;
  needs_clarification: boolean;
  clarification_question: string;
  workflow_steps: string[];
  required_documents: string[];
  authorities: Array<string | { name?: string; [key: string]: unknown }>;
  relevant_laws: string[];
  complaint_template?: string | null;
  online_portals: string[];
  helplines: string[];
  embedding_score: number;
  final_confidence: number;
}

export function classifyIssue(payload: ClassifyPayload): Promise<ClassifyResponse> {
  return request<ClassifyResponse>("/api/classify", {
    method: "POST",
    body: JSON.stringify(payload),
  }, true);
}
