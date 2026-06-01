import axios from "axios";
import type { RoleProfile, User, UserRole } from "@/types";
import { normalizeRole } from "@/lib/rbac";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const API_BASE_URL = BASE_URL.replace(/\/$/, "");

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || "";
    const isAuthProbe =
      url.includes("/auth/me") ||
      url.includes("/auth/login") ||
      url.includes("/auth/logout") ||
      url.includes("/auth/register") ||
      url.includes("/auth/roles");
    if (status === 401 && !isAuthProbe) {
      window.dispatchEvent(new CustomEvent("devops-auth:unauthorized"));
    }
    return Promise.reject(err);
  },
);

export interface LoginResponse {
  user?: User;
  user_id?: string;
  username?: string;
  role?: string;
  email?: string;
  id?: string;
  is_active?: boolean;
  created_at?: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  role: Extract<UserRole, "developer" | "viewer">;
}

export interface AdminCreateUserRequest {
  email: string;
  username: string;
  password: string;
  role: UserRole;
  is_active?: boolean;
}

function normalizeUser(data: LoginResponse | User): User {
  if ("user" in data && data.user)
    return { ...data.user, role: normalizeRole(data.user.role) };
  return {
    id: data.id || ("user_id" in data && data.user_id ? data.user_id : ""),
    email: data.email,
    username: data.username || "",
    role: normalizeRole(data.role),
    is_active: data.is_active,
    created_at: data.created_at,
  };
}

export const authService = {
  login: async (email: string, password: string): Promise<User> => {
    const res = await api.post<LoginResponse>("/auth/login", {
      email,
      password,
    });
    return normalizeUser(res.data);
  },
  register: async ({
    email,
    username,
    password,
    role,
  }: RegisterRequest): Promise<User> => {
    const res = await api.post<LoginResponse>("/auth/register", {
      email,
      username,
      password,
      role,
    });
    return normalizeUser(res.data);
  },
  me: async (): Promise<User> => {
    const res = await api.get<User>("/auth/me");
    return normalizeUser(res.data);
  },
  logout: async (): Promise<void> => {
    await api.post("/auth/logout");
  },
  roles: async (): Promise<RoleProfile[]> => {
    const res = await api.get<{ roles: RoleProfile[] }>("/auth/roles");
    return res.data.roles;
  },
  listUsers: async (): Promise<User[]> => {
    const res = await api.get<User[]>("/auth/users");
    return res.data.map(normalizeUser);
  },
  createUser: async (payload: AdminCreateUserRequest): Promise<User> => {
    const res = await api.post<User>("/auth/users", payload);
    return normalizeUser(res.data);
  },
};

export const agentService = {
  chat: async (message: string, sessionId?: string) => {
    const res = await api.post("/agent/chat", {
      message,
      session_id: sessionId,
    });
    return res.data;
  },
  orchestrate: async (
    message: string,
    context: Record<string, unknown> = {},
  ): Promise<AgentOrchestrationResult> => {
    const res = await api.post<AgentOrchestrationResult>("/agent/orchestrate", {
      message,
      context,
    });
    return res.data;
  },
  clearSession: async (sessionId: string) => {
    await api.delete(`/agent/session/${sessionId}`);
  },
};

export interface AgentOrchestrationResult {
  selected_agent: string;
  intent: string;
  risk_level: string;
  success: boolean;
  result: string;
  metadata: Record<string, unknown>;
}

export const approvalService = {
  list: async () => {
    const res = await api.get("/approvals");
    return res.data;
  },
  decide: async (approvalId: string, approved: boolean, note?: string) => {
    const res = await api.post(`/approvals/${approvalId}/decide`, {
      approved,
      note,
    });
    return res.data;
  },
};

export const executionService = {
  list: async (
    params: {
      limit?: number;
      tool?: string | null;
      status?: string | null;
      actor?: string | null;
      source?: string | null;
      days?: number;
    } = {},
  ) => {
    const cleaned = Object.fromEntries(
      Object.entries({ limit: 50, ...params }).filter(
        ([, value]) => value !== null && value !== undefined && value !== "",
      ),
    );
    const res = await api.get("/audit", { params: cleaned });
    return res.data;
  },
  get: async (id: string) => {
    const res = await api.get(`/executions/${id}`);
    return res.data;
  },
};

export interface WorkflowFailure {
  id: string;
  repo_full_name: string;
  workflow_run_id: number;
  workflow_name: string | null;
  branch: string | null;
  conclusion: string;
  workflow_url: string | null;
  log_excerpt: string | null;
  predicted_label: string | null;
  confidence: number | null;
  suggested_fix: string | null;
  recommendation?: Record<string, unknown> | null;
  fix_pr_url: string | null;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface WorkflowFailureFixPRResult {
  workflow_failure_id: string;
  repo_full_name: string;
  status: string;
  approval_id?: string | null;
  branch?: string | null;
  workflow_path?: string | null;
  pull_request_url?: string | null;
  message: string;
  recommendation?: Record<string, unknown> | null;
  approval_details?: Record<string, unknown> | null;
}

export const workflowFailureService = {
  list: async (limit = 50): Promise<WorkflowFailure[]> => {
    const res = await api.get<WorkflowFailure[]>("/workflow-failures", {
      params: { limit },
    });
    return res.data;
  },
  get: async (id: string): Promise<WorkflowFailure> => {
    const res = await api.get<WorkflowFailure>(`/workflow-failures/${id}`);
    return res.data;
  },
  createFixPr: async (id: string): Promise<WorkflowFailureFixPRResult> => {
    const res = await api.post<WorkflowFailureFixPRResult>(
      `/workflow-failures/${id}/create-fix-pr`,
    );
    return res.data;
  },
};

export interface FailurePrediction {
  label: string;
  confidence: number | null;
  suggested_fix: string;
  recommendation?: Record<string, unknown>;
}

export interface DetectedStack {
  language: string;
  framework: string;
  package_manager: string;
  has_docker: boolean;
  has_existing_workflows: boolean;
  recommended_workflow: string;
}

export interface GeneratedWorkflow {
  stack: DetectedStack;
  path: string;
  workflow_yaml: string;
}

export interface RepositoryScanResult {
  repo_full_name: string;
  files: string[];
  stack: DetectedStack;
}

export interface WorkflowPRResult {
  repo_full_name: string;
  detected_stack: DetectedStack;
  branch: string;
  workflow_path: string;
  pull_request_url: string;
}

export const repositoryService = {
  scan: async (repoFullName: string): Promise<RepositoryScanResult> => {
    const res = await api.post<RepositoryScanResult>("/repositories/scan", {
      repo_full_name: repoFullName,
    });
    return res.data;
  },
  createWorkflowPr: async (repoFullName: string): Promise<WorkflowPRResult> => {
    const res = await api.post<WorkflowPRResult>(
      "/repositories/create-workflow-pr",
      { repo_full_name: repoFullName },
    );
    return res.data;
  },
};

export const cicdAssistantService = {
  predictFailure: async (logText: string): Promise<FailurePrediction> => {
    const res = await api.post<FailurePrediction>("/model/predict-failure", {
      log_text: logText,
    });
    return res.data;
  },
  generateWorkflow: async (files: string[]): Promise<GeneratedWorkflow> => {
    const res = await api.post<GeneratedWorkflow>("/cicd/generate-workflow", {
      files,
    });
    return res.data;
  },
};
