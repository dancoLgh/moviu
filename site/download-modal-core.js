(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.MoviuDownload = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function normalizeDonationAmount(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount) || amount <= 0) {
      throw new TypeError("Donation amount must be a positive number");
    }
    return amount;
  }

  function createDownloadScheduler(options = {}) {
    const duration = options.duration ?? 3;
    const setIntervalFn = options.setIntervalFn ?? setInterval;
    const clearIntervalFn = options.clearIntervalFn ?? clearInterval;

    function schedule(url, callbacks = {}) {
      if (!url) {
        throw new TypeError("A download URL is required");
      }

      let remaining = duration;
      let started = false;
      let timer;
      const onTick = callbacks.onTick ?? (() => {});
      const onStart = callbacks.onStart ?? (() => {});
      const job = {
        url,
        get started() {
          return started;
        },
        startNow() {
          if (started) return false;
          started = true;
          if (timer !== undefined) clearIntervalFn(timer);
          onTick(0);
          onStart(url);
          return true;
        },
      };

      timer = setIntervalFn(() => {
        if (started) return;
        remaining -= 1;
        onTick(Math.max(remaining, 0));
        if (remaining <= 0) job.startNow();
      }, 1000);
      return job;
    }

    return { schedule };
  }

  function createExternalScriptLoader(options) {
    const documentObject = options.documentObject;
    const src = options.src;
    const resolveValue = options.resolveValue;
    const timeoutMs = options.timeoutMs ?? 10000;
    const setTimeoutFn = options.setTimeoutFn ?? setTimeout;
    const clearTimeoutFn = options.clearTimeoutFn ?? clearTimeout;
    let loadingPromise;

    function load() {
      const loadedValue = resolveValue();
      if (loadedValue) return Promise.resolve(loadedValue);
      if (loadingPromise) return loadingPromise;

      loadingPromise = new Promise((resolve, reject) => {
        const existingScript = documentObject.querySelector(`script[src="${src}"]`);
        const script = existingScript || documentObject.createElement("script");
        let settled = false;
        let timeout;
        const cleanup = (preserveListeners = false) => {
          clearTimeoutFn(timeout);
          if (preserveListeners) return;
          script.removeEventListener("load", handleLoad);
          script.removeEventListener("error", handleError);
        };
        const rejectLoad = (error, removeScript = false, preserveListeners = false) => {
          if (settled) return;
          settled = true;
          cleanup(preserveListeners);
          if (removeScript) script.remove();
          loadingPromise = undefined;
          reject(error);
        };
        const handleLoad = () => {
          const value = resolveValue();
          if (settled) {
            cleanup();
            if (!value) script.remove();
            return;
          }
          if (!value) {
            rejectLoad(new Error("External script loaded without the expected value"));
            return;
          }
          settled = true;
          cleanup();
          resolve(value);
        };
        const handleError = () => {
          if (settled) {
            cleanup();
            script.remove();
            return;
          }
          rejectLoad(new Error("External script failed to load"), true);
        };

        script.addEventListener("load", handleLoad, { once: true });
        script.addEventListener("error", handleError, { once: true });
        timeout = setTimeoutFn(
          () => rejectLoad(new Error("External script timed out"), false, true),
          timeoutMs
        );
        if (!existingScript) {
          script.src = src;
          script.async = true;
          documentObject.body.appendChild(script);
        }
      });
      return loadingPromise;
    }

    return { load };
  }

  return { createDownloadScheduler, createExternalScriptLoader, normalizeDonationAmount };
});
