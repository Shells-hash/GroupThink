import { api } from "../api.js";
import { setToken, setUser } from "../state.js";
import { navigate } from "../router.js";

const GOOGLE_BTN = `
  <button class="btn-google" id="google-btn">
    <svg width="18" height="18" viewBox="0 0 48 48">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
    Continue with Google
  </button>
  <div class="auth-divider"><span>or</span></div>
`;

export function renderLogin() {
  document.getElementById("app").innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">Group<span>Think</span></div>
        ${GOOGLE_BTN}
        <div class="form-group">
          <label>Username</label>
          <input class="input" id="username" placeholder="Enter username" autocomplete="username" />
        </div>
        <div class="form-group" style="margin-top:16px">
          <label>Password</label>
          <input class="input" id="password" type="password" placeholder="Enter password" autocomplete="current-password" />
        </div>
        <div style="text-align:right;margin-top:6px">
          <a href="#/forgot-password" style="font-size:12px;color:var(--color-primary)">Forgot password?</a>
        </div>
        <div id="auth-error" style="margin-top:12px;display:none"></div>
        <button class="btn btn-primary btn-full" id="login-btn" style="margin-top:16px">Sign in</button>
        <p style="margin-top:16px;font-size:13px;color:var(--color-text-muted);text-align:center">
          No account? <a href="#/register" style="color:var(--color-primary)">Create one</a>
        </p>
      </div>
    </div>
  `;

  // Show any error passed back in the URL (e.g. from OAuth redirect)
  const hashQuery = location.hash.includes("?") ? location.hash.split("?")[1] : "";
  const urlError = new URLSearchParams(hashQuery).get("error");
  if (urlError) _showError(decodeURIComponent(urlError));

  document.getElementById("google-btn").addEventListener("click", () => {
    window.location.href = "/auth/google";
  });

  document.getElementById("login-btn").addEventListener("click", async () => {
    const btn = document.getElementById("login-btn");
    btn.disabled = true; btn.textContent = "Signing in…";
    try {
      const res = await api.login({
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
      });
      setToken(res.access_token);
      setUser(await api.me());
      navigate("/groups");
    } catch (e) {
      _showError(e.message);
    } finally {
      btn.disabled = false; btn.textContent = "Sign in";
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
        ${GOOGLE_BTN}
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
          <input class="input" id="password" type="password" placeholder="At least 8 characters" />
        </div>
        <div id="auth-error" style="margin-top:12px;display:none"></div>
        <button class="btn btn-primary btn-full" id="reg-btn" style="margin-top:20px">Create account</button>
        <p style="margin-top:16px;font-size:13px;color:var(--color-text-muted);text-align:center">
          Have an account? <a href="#/login" style="color:var(--color-primary)">Sign in</a>
        </p>
      </div>
    </div>
  `;

  document.getElementById("google-btn").addEventListener("click", () => {
    window.location.href = "/auth/google";
  });

  document.getElementById("reg-btn").addEventListener("click", async () => {
    const btn = document.getElementById("reg-btn");
    btn.disabled = true; btn.textContent = "Creating…";
    try {
      const res = await api.register({
        username: document.getElementById("username").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
      });
      setToken(res.access_token);
      setUser(await api.me());
      navigate("/groups");
    } catch (e) {
      _showError(e.message);
    } finally {
      btn.disabled = false; btn.textContent = "Create account";
    }
  });
}

export function renderForgotPassword() {
  document.getElementById("app").innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">Group<span>Think</span></div>
        <h3 style="margin-bottom:8px;font-size:16px">Reset your password</h3>
        <p style="font-size:13px;color:var(--color-text-muted);margin-bottom:20px">
          Enter your email and we'll send you a reset link.
        </p>
        <div class="form-group">
          <label>Email</label>
          <input class="input" id="email" type="email" placeholder="your@email.com" />
        </div>
        <div id="auth-error" style="margin-top:12px;display:none"></div>
        <div id="auth-success" style="margin-top:12px;display:none"></div>
        <button class="btn btn-primary btn-full" id="submit-btn" style="margin-top:20px">Send reset link</button>
        <p style="margin-top:16px;font-size:13px;color:var(--color-text-muted);text-align:center">
          <a href="#/login" style="color:var(--color-primary)">← Back to sign in</a>
        </p>
      </div>
    </div>
  `;

  document.getElementById("submit-btn").addEventListener("click", async () => {
    const btn = document.getElementById("submit-btn");
    btn.disabled = true; btn.textContent = "Sending…";
    try {
      await api.forgotPassword(document.getElementById("email").value);
      const s = document.getElementById("auth-success");
      s.style.display = "block";
      s.className = "error-msg";
      s.style.borderColor = "var(--color-success)";
      s.style.color = "var(--color-success)";
      s.style.background = "rgba(104,211,145,0.1)";
      s.textContent = "If that email is registered, a reset link has been sent. Check your inbox.";
      btn.style.display = "none";
    } catch (e) {
      _showError(e.message);
      btn.disabled = false; btn.textContent = "Send reset link";
    }
  });
}

export function renderResetPassword(token) {
  document.getElementById("app").innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">Group<span>Think</span></div>
        <h3 style="margin-bottom:8px;font-size:16px">Choose a new password</h3>
        <div class="form-group" style="margin-top:16px">
          <label>New password</label>
          <input class="input" id="password" type="password" placeholder="At least 8 characters" />
        </div>
        <div class="form-group" style="margin-top:16px">
          <label>Confirm password</label>
          <input class="input" id="confirm" type="password" placeholder="Repeat your password" />
        </div>
        <div id="auth-error" style="margin-top:12px;display:none"></div>
        <button class="btn btn-primary btn-full" id="reset-btn" style="margin-top:20px">Reset password</button>
      </div>
    </div>
  `;

  document.getElementById("reset-btn").addEventListener("click", async () => {
    const btn = document.getElementById("reset-btn");
    const pw = document.getElementById("password").value;
    const confirm = document.getElementById("confirm").value;
    if (pw !== confirm) return _showError("Passwords don't match");
    if (pw.length < 8) return _showError("Password must be at least 8 characters");

    btn.disabled = true; btn.textContent = "Resetting…";
    try {
      await api.resetPassword(token, pw);
      document.getElementById("app").innerHTML = `
        <div class="auth-page">
          <div class="auth-card" style="text-align:center">
            <div class="logo">Group<span>Think</span></div>
            <p style="color:var(--color-success);font-size:15px;margin-bottom:16px">Password reset successfully!</p>
            <a href="#/login" class="btn btn-primary">Sign in</a>
          </div>
        </div>
      `;
    } catch (e) {
      _showError(e.message);
      btn.disabled = false; btn.textContent = "Reset password";
    }
  });
}

function _showError(msg) {
  const el = document.getElementById("auth-error");
  el.className = "error-msg";
  el.style.display = "block";
  el.textContent = msg;
}
