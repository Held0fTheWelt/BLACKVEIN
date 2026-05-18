(function () {
  function setFormDisabled(form, disabled) {
    if (!form || !form.elements) return;
    Array.prototype.forEach.call(form.elements, function (el) {
      if (el && typeof el.disabled === "boolean") {
        el.disabled = !!disabled;
      }
    });
  }

  function setStatus(text) {
    const status = document.getElementById("play-launcher-status");
    if (status) {
      status.textContent = text;
    }
  }

  function readJsonResponse(response) {
    return response.json().catch(function () {
      return {};
    }).then(function (data) {
      return {
        ok: response.ok,
        data: data || {},
      };
    });
  }

  function responseError(data, fallback) {
    if (data && data.error) return data.error;
    if (data && data.error_detail) return data.error_detail;
    return fallback;
  }

  function submitStart(form, state) {
    if (state.pending) return;
    if (typeof form.reportValidity === "function" && !form.reportValidity()) return;

    const body = new FormData(form);
    body.set("skip_graph_opening_on_create", "1");
    state.pending = true;
    setFormDisabled(form, true);
    setStatus("Starting session...");

    fetch(form.action, {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      credentials: "same-origin",
      body,
    })
      .then(readJsonResponse)
      .then(function (result) {
        if (!result.ok || result.data.ok === false) {
          throw new Error(responseError(result.data, "Could not start game session."));
        }
        const redirectUrl = result.data.redirect_url;
        if (!redirectUrl) {
          throw new Error("Player session creation returned no redirect URL.");
        }
        window.location.assign(redirectUrl);
      })
      .catch(function (err) {
        setStatus((err && err.message) || "Network error. Try again.");
        state.pending = false;
        setFormDisabled(form, false);
      });
  }

  function init() {
    const form = document.getElementById("play-launcher-form");
    if (!form || form.dataset.sessionStartEnhanced === "true") return false;

    const state = { pending: false };
    form.dataset.sessionStartEnhanced = "true";
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      submitStart(form, state);
    });
    return true;
  }

  window.PlaySessionStart = {
    init,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
