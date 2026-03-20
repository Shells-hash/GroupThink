const routes = {};

export function route(pattern, handler) {
  routes[pattern] = handler;
}

export function navigate(path) {
  location.hash = path;
}

export function initRouter() {
  window.addEventListener("hashchange", _resolve);
  _resolve();
}

function _resolve() {
  const raw = location.hash.slice(1) || "/";
  const hash = raw.split("?")[0]; // strip query string before route matching
  // Try exact match first, then pattern match
  for (const [pattern, handler] of Object.entries(routes)) {
    const params = _match(pattern, hash);
    if (params !== null) {
      handler(params);
      return;
    }
  }
}

function _match(pattern, path) {
  const pParts = pattern.split("/");
  const hParts = path.split("/");
  if (pParts.length !== hParts.length) return null;
  const params = {};
  for (let i = 0; i < pParts.length; i++) {
    if (pParts[i].startsWith(":")) {
      params[pParts[i].slice(1)] = hParts[i];
    } else if (pParts[i] !== hParts[i]) {
      return null;
    }
  }
  return params;
}
