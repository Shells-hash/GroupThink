import { api } from "../api.js";
import { setToken, setUser } from "../state.js";
import { navigate } from "../router.js";

export function renderLogin() {
  document.getElementById("app").innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">Group<span>Think</span></div>
        <div class="form-group">
          <label>Username</label>
          <input class="input" id="username" placeholder="Enter username" autocomplete="username" />
        </div>
        <div class="form-group" style="margin-top:16px">
          <label>Password</label>
          <input class="input" id="password" type="password" placeholder="Enter password" autocomplete="current-password" />
        </div>
        <div id="auth-error" style="margin-top:12px;display:none"></div>
        <button class="btn btn-primary btn-full" id="login-btn" style="margin-top:20px">Sign in</button>
        <p style="margin-top:16px;font-size:13px;color:var(--color-text-muted);text-align:center">
          No account? <a href="#/register" style="color:var(--color-primary)">Create one</a>
        </p>
      </div>
    </div>
  `;

  document.getElementById("login-btn").addEventListener("click", async () => {
    const btn = document.getElementById("login-btn");
    btn.disabled = true;
    btn.textContent = "Signing in…";
    try {
      const res = await api.login({
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
      });
      setToken(res.access_token);
      const user = await api.me();
      setUser(user);
      navigate("/groups");
    } catch (e) {
      _showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Sign in";
    }
  });

  document.getElementById("password").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("login-btn").click();
  });
}

export function renderRegister() {
  document.getElementById("app").innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">Group<span>Think</span></div>
        <div class="form-group">
          <label>Username</label>
          <input class="input" id="username" placeholder="Choose a username" />
        </div>
        <div class="form-group" style="margin-top:16px">
          <label>Email</label>
          <input class="input" id="email" type="email" placeholder="your@email.com" />
        </div>
        <div class="form-group" style="margin-top:16px">
          <label>Password</label>
          <input class="input" id="password" type="password" placeholder="Choose a password" />
        </div>
        <div id="auth-error" style="margin-top:12px;display:none"></div>
        <button class="btn btn-primary btn-full" id="reg-btn" style="margin-top:20px">Create account</button>
        <p style="margin-top:16px;font-size:13px;color:var(--color-text-muted);text-align:center">
          Have an account? <a href="#/login" style="color:var(--color-primary)">Sign in</a>
        </p>
      </div>
    </div>
  `;

  document.getElementById("reg-btn").addEventListener("click", async () => {
    const btn = document.getElementById("reg-btn");
    btn.disabled = true;
    btn.textContent = "Creating…";
    try {
      const res = await api.register({
        username: document.getElementById("username").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
      });
      setToken(res.access_token);
      const user = await api.me();
      setUser(user);
      navigate("/groups");
    } catch (e) {
      _showError(e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Create account";
    }
  });
}

function _showError(msg) {
  const el = document.getElementById("auth-error");
  el.className = "error-msg";
  el.style.display = "block";
  el.textContent = msg;
}
