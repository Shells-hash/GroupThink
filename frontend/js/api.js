import { state } from "./state.js";

const BASE = "";

async function request(method, path, body = null) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

export const api = {
  // Auth
  register: (body) => request("POST", "/auth/register", body),
  login: (body) => request("POST", "/auth/login", body),
  me: () => request("GET", "/auth/me"),
  forgotPassword: (email) => request("POST", "/auth/forgot-password", { email }),
  resetPassword: (token, new_password) => request("POST", "/auth/reset-password", { token, new_password }),

  // Groups
  getGroups: () => request("GET", "/groups"),
  createGroup: (body) => request("POST", "/groups", body),
  getGroup: (id) => request("GET", `/groups/${id}`),
  deleteGroup: (id) => request("DELETE", `/groups/${id}`),
  inviteMember: (groupId, body) => request("POST", `/groups/${groupId}/invite`, body),
  removeMember: (groupId, userId) => request("DELETE", `/groups/${groupId}/members/${userId}`),

  // Threads
  getThreads: (groupId) => request("GET", `/groups/${groupId}/threads`),
  createThread: (groupId, body) => request("POST", `/groups/${groupId}/threads`, body),
  deleteThread: (groupId, threadId) => request("DELETE", `/groups/${groupId}/threads/${threadId}`),

  // Messages
  getMessages: (threadId, params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request("GET", `/threads/${threadId}/messages${q ? "?" + q : ""}`);
  },

  // Plans
  getPlan: (threadId) => request("GET", `/plans/${threadId}`),
  generatePlan: (threadId) => request("POST", `/plans/${threadId}/generate`),

  // Plan chat
  getPlanChat: (threadId) => request("GET", `/plan-chat/${threadId}`),
  sendPlanChat: (threadId, message) => request("POST", `/plan-chat/${threadId}`, { message }),

  // Documents
  getDocs: (threadId) => request("GET", `/threads/${threadId}/docs`),
  createDoc: (threadId, body) => request("POST", `/threads/${threadId}/docs`, body),
  generateDoc: (threadId, body) => request("POST", `/threads/${threadId}/docs/generate`, body),
  getDoc: (docId) => request("GET", `/docs/${docId}`),
  updateDoc: (docId, body) => request("PUT", `/docs/${docId}`, body),
  deleteDoc: (docId) => request("DELETE", `/docs/${docId}`),
  aiDraftDoc: (docId) => request("POST", `/docs/${docId}/ai-draft`),
};
