const test = require("node:test");
const assert = require("node:assert/strict");

const {
  createDownloadScheduler,
  createExternalScriptLoader,
  normalizeDonationAmount,
} = require("../../site/download-modal-core.js");

function fakeScriptDocument() {
  const scripts = [];
  function createScript() {
    const listeners = new Map();
    return {
      listeners,
      removed: false,
      addEventListener(name, callback) {
        listeners.set(name, callback);
      },
      removeEventListener(name) {
        listeners.delete(name);
      },
      remove() {
        this.removed = true;
        const index = scripts.indexOf(this);
        if (index >= 0) scripts.splice(index, 1);
      },
    };
  }
  return {
    scripts,
    createElement: createScript,
    querySelector() {
      return scripts[0] || null;
    },
    body: {
      appendChild(script) {
        scripts.push(script);
      },
    },
  };
}

test("normalizes checkout amounts to numbers", () => {
  assert.equal(normalizeDonationAmount("10"), 10);
  assert.throws(() => normalizeDonationAmount("invalid"), TypeError);
});

test("keeps separately selected downloads scheduled", () => {
  const intervals = [];
  const downloads = [];
  const scheduler = createDownloadScheduler({
    setIntervalFn(callback) {
      intervals.push(callback);
      return intervals.length;
    },
    clearIntervalFn() {},
  });

  scheduler.schedule("windows.exe", { onStart: (url) => downloads.push(url) });
  scheduler.schedule("linux", { onStart: (url) => downloads.push(url) });
  intervals.forEach((tick) => {
    tick();
    tick();
    tick();
  });

  assert.deepEqual(downloads, ["windows.exe", "linux"]);
});

test("starts each scheduled download at most once", () => {
  let interval;
  let starts = 0;
  const scheduler = createDownloadScheduler({
    setIntervalFn(callback) {
      interval = callback;
      return 1;
    },
    clearIntervalFn() {},
  });
  const job = scheduler.schedule("moviu", { onStart: () => starts++ });

  assert.equal(job.startNow(), true);
  assert.equal(job.startNow(), false);
  interval();
  assert.equal(starts, 1);
});

test("timeout retries observe the same script without reinserting it", async () => {
  const documentObject = fakeScriptDocument();
  const timeouts = [];
  const loader = createExternalScriptLoader({
    documentObject,
    src: "https://example.com/sdk.js",
    resolveValue: () => null,
    setTimeoutFn(callback) {
      timeouts.push(callback);
      return timeouts.length;
    },
    clearTimeoutFn() {},
  });

  const firstLoad = loader.load();
  timeouts[0]();
  await assert.rejects(firstLoad, /timed out/);
  assert.equal(documentObject.scripts.length, 1);

  const secondLoad = loader.load();
  assert.equal(documentObject.scripts.length, 1);
  timeouts[1]();
  await assert.rejects(secondLoad, /timed out/);
});

test("network errors remove the failed script before retrying", async () => {
  const documentObject = fakeScriptDocument();
  const loader = createExternalScriptLoader({
    documentObject,
    src: "https://example.com/sdk.js",
    resolveValue: () => null,
    setTimeoutFn() {
      return 1;
    },
    clearTimeoutFn() {},
  });

  const firstLoad = loader.load();
  documentObject.scripts[0].listeners.get("error")();
  await assert.rejects(firstLoad, /failed to load/);
  assert.equal(documentObject.scripts.length, 0);

  loader.load();
  assert.equal(documentObject.scripts.length, 1);
});

test("a network error after timeout removes the stale script", async () => {
  const documentObject = fakeScriptDocument();
  const timeouts = [];
  const loader = createExternalScriptLoader({
    documentObject,
    src: "https://example.com/sdk.js",
    resolveValue: () => null,
    setTimeoutFn(callback) {
      timeouts.push(callback);
      return timeouts.length;
    },
    clearTimeoutFn() {},
  });

  const firstLoad = loader.load();
  const staleScript = documentObject.scripts[0];
  timeouts[0]();
  await assert.rejects(firstLoad, /timed out/);
  staleScript.listeners.get("error")();
  assert.equal(documentObject.scripts.length, 0);

  loader.load();
  assert.equal(documentObject.scripts.length, 1);
});

test("a successful load after timeout keeps and reuses the original script", async () => {
  const documentObject = fakeScriptDocument();
  const timeouts = [];
  let constructor = null;
  const loader = createExternalScriptLoader({
    documentObject,
    src: "https://example.com/sdk.js",
    resolveValue: () => constructor,
    setTimeoutFn(callback) {
      timeouts.push(callback);
      return timeouts.length;
    },
    clearTimeoutFn() {},
  });

  const firstLoad = loader.load();
  const originalScript = documentObject.scripts[0];
  timeouts[0]();
  await assert.rejects(firstLoad, /timed out/);
  constructor = class DlocalGo {};
  originalScript.listeners.get("load")();

  assert.equal(documentObject.scripts.length, 1);
  assert.equal(await loader.load(), constructor);
});
