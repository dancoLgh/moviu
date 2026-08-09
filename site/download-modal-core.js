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

  return { createDownloadScheduler, normalizeDonationAmount };
});
