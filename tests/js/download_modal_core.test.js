const test = require("node:test");
const assert = require("node:assert/strict");

const {
  createDownloadScheduler,
  normalizeDonationAmount,
} = require("../../site/download-modal-core.js");

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
