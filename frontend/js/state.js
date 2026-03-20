export const state = {
  user: null,        // { id, username, email }
  token: null,       // JWT string
  groups: [],        // list of group objects
  activeGroup: null,
  threads: [],
  activeThread: null,
  messages: [],
};

export function setUser(user) { state.user = user; }
export function setToken(token) {
  state.token = token;
  if (token) localStorage.setItem("gt_token", token);
  else localStorage.removeItem("gt_token");
}
export function loadToken() {
  state.token = localStorage.getItem("gt_token") || null;
}
