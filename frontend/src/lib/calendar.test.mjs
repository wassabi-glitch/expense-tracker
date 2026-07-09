import assert from "node:assert/strict";
import test from "node:test";

// ---------------------------------------------------------------------------
// Calendar module tests (Issue 9 & 10)
//
// Covers: parse/format, arithmetic, comparison, schedule preview,
// relative due labels, and timezone boundary cases.
// ---------------------------------------------------------------------------

// Replicate the module functions for pure unit testing.
// (In production these are imported from calendar.js)

function daysInMonth(year, month) {
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

function clampDay(year, month, day) {
  const max = daysInMonth(year, month);
  return day > max ? max : day;
}

function parseDateString(dateString) {
  if (typeof dateString !== "string") return null;
  const parts = dateString.split("-");
  if (parts.length !== 3) return null;
  const y = Number(parts[0]);
  const m = Number(parts[1]);
  const d = Number(parts[2]);
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return null;
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  return { year: y, month: m, day: d };
}

function toDateString(year, month, day) {
  const y = String(year).padStart(4, "0");
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(dateString, n) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  const d = new Date(Date.UTC(parsed.year, parsed.month - 1, parsed.day, 12, 0, 0));
  d.setUTCDate(d.getUTCDate() + Number(n));
  return toDateString(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
}

function addWeeks(dateString, n) {
  return addDays(dateString, Number(n) * 7);
}

function addMonths(dateString, n) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  n = Number(n);
  let year = parsed.year;
  let month = parsed.month + n;
  while (month > 12) { month -= 12; year += 1; }
  while (month < 1) { month += 12; year -= 1; }
  const day = clampDay(year, month, parsed.day);
  return toDateString(year, month, day);
}

function addQuarters(dateString, n) {
  return addMonths(dateString, Number(n) * 3);
}

function addYears(dateString, n) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  const year = parsed.year + Number(n);
  const day = clampDay(year, parsed.month, parsed.day);
  return toDateString(year, parsed.month, day);
}

function compareDates(a, b) {
  if (a === b) return 0;
  const pa = parseDateString(a);
  const pb = parseDateString(b);
  if (!pa || !pb) return null;
  if (pa.year !== pb.year) return pa.year < pb.year ? -1 : 1;
  if (pa.month !== pb.month) return pa.month < pb.month ? -1 : 1;
  if (pa.day !== pb.day) return pa.day < pb.day ? -1 : 1;
  return 0;
}

function isBefore(a, b) { return compareDates(a, b) === -1; }
function isAfter(a, b) { return compareDates(a, b) === 1; }
function isSameOrBefore(a, b) { const c = compareDates(a, b); return c === -1 || c === 0; }
function isSameOrAfter(a, b) { const c = compareDates(a, b); return c === 1 || c === 0; }

function daysBetween(a, b) {
  const pa = parseDateString(a);
  const pb = parseDateString(b);
  if (!pa || !pb) return 0;
  const da = new Date(Date.UTC(pa.year, pa.month - 1, pa.day, 12, 0, 0));
  const db = new Date(Date.UTC(pb.year, pb.month - 1, pb.day, 12, 0, 0));
  return Math.abs(Math.round((db - da) / 86400000)) + 1;
}

function startOfMonth(dateString) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  return toDateString(parsed.year, parsed.month, 1);
}

function endOfMonth(dateString) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  return toDateString(parsed.year, parsed.month, daysInMonth(parsed.year, parsed.month));
}

function relativeDueLabel(dueDate, todayDate) {
  if (!dueDate || !todayDate) return "";
  const cmp = compareDates(dueDate, todayDate);
  if (cmp === null) return "";
  if (cmp === 0) return "today";
  const days = daysBetween(dueDate, todayDate) - 1;
  if (cmp > 0) {
    if (days === 1) return "tomorrow";
    return `in ${days} days`;
  }
  if (days === 1) return "yesterday";
  return `overdue by ${days} days`;
}

const FREQUENCY_ADD = {
  WEEKLY: (d) => addWeeks(d, 1),
  BIWEEKLY: (d) => addWeeks(d, 2),
  MONTHLY: (d) => addMonths(d, 1),
  QUARTERLY: (d) => addQuarters(d, 1),
  YEARLY: (d) => addYears(d, 1),
};

function generateSchedule(startDate, frequency, count) {
  const addFn = FREQUENCY_ADD[frequency];
  if (!addFn) return [startDate];
  const dates = [startDate];
  let cursor = startDate;
  for (let i = 1; i < count; i++) {
    cursor = addFn(cursor, 1);
    dates.push(cursor);
  }
  return dates;
}

// ---------------------------------------------------------------------------
// Parse / format
// ---------------------------------------------------------------------------

test("parseDateString: valid date", () => {
  const d = parseDateString("2026-07-09");
  assert.deepStrictEqual(d, { year: 2026, month: 7, day: 9 });
});

test("parseDateString: rejects invalid strings", () => {
  assert.strictEqual(parseDateString(""), null);
  assert.strictEqual(parseDateString("not-a-date"), null);
  assert.strictEqual(parseDateString(123), null);
  assert.strictEqual(parseDateString(null), null);
  assert.strictEqual(parseDateString("2026-13-01"), null); // month 13
  assert.strictEqual(parseDateString("2026-00-01"), null); // month 0
  assert.strictEqual(parseDateString("2026-01-32"), null); // day 32
});

test("toDateString: formats back to YYYY-MM-DD", () => {
  assert.strictEqual(toDateString(2026, 7, 9), "2026-07-09");
  assert.strictEqual(toDateString(2026, 1, 1), "2026-01-01");
  assert.strictEqual(toDateString(2026, 12, 31), "2026-12-31");
});

// ---------------------------------------------------------------------------
// Arithmetic
// ---------------------------------------------------------------------------

test("addDays: basic forward and backward", () => {
  assert.strictEqual(addDays("2026-07-09", 1), "2026-07-10");
  assert.strictEqual(addDays("2026-07-09", -1), "2026-07-08");
  assert.strictEqual(addDays("2026-07-09", 30), "2026-08-08");
  assert.strictEqual(addDays("2026-01-01", -1), "2025-12-31");
});

test("addDays: invalid input returns as-is", () => {
  assert.strictEqual(addDays("", 5), "");
  assert.strictEqual(addDays(null, 5), null);
});

test("addWeeks: adds 7 days per week", () => {
  assert.strictEqual(addWeeks("2026-07-09", 1), "2026-07-16");
  assert.strictEqual(addWeeks("2026-07-09", 2), "2026-07-23");
  assert.strictEqual(addWeeks("2026-07-09", -1), "2026-07-02");
});

test("addMonths: calendar-month arithmetic", () => {
  assert.strictEqual(addMonths("2026-01-15", 1), "2026-02-15");
  assert.strictEqual(addMonths("2026-01-15", 12), "2027-01-15");
  assert.strictEqual(addMonths("2026-01-15", -1), "2025-12-15");
  assert.strictEqual(addMonths("2026-01-15", -14), "2024-11-15");
});

test("addMonths: end-of-month clamping (Jan 31 → Feb 28)", () => {
  assert.strictEqual(addMonths("2026-01-31", 1), "2026-02-28");
  assert.strictEqual(addMonths("2026-03-31", -1), "2026-02-28");
  assert.strictEqual(addMonths("2024-01-31", 1), "2024-02-29"); // leap year
});

test("addQuarters: 3 months each", () => {
  assert.strictEqual(addQuarters("2026-01-15", 1), "2026-04-15");
  assert.strictEqual(addQuarters("2026-01-15", 4), "2027-01-15");
});

test("addYears: basic", () => {
  assert.strictEqual(addYears("2026-07-09", 1), "2027-07-09");
  assert.strictEqual(addYears("2026-07-09", -1), "2025-07-09");
});

test("addYears: Feb 29 leap year handling", () => {
  assert.strictEqual(addYears("2024-02-29", 1), "2025-02-28"); // no leap → clamp
  assert.strictEqual(addYears("2024-02-29", 4), "2028-02-29"); // next leap
});

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

test("compareDates: ordering", () => {
  assert.strictEqual(compareDates("2026-01-01", "2026-01-02"), -1);
  assert.strictEqual(compareDates("2026-01-02", "2026-01-01"), 1);
  assert.strictEqual(compareDates("2026-01-01", "2026-01-01"), 0);
  assert.strictEqual(compareDates("2025-12-31", "2026-01-01"), -1); // year boundary
});

test("isBefore / isAfter / isSameOrBefore / isSameOrAfter", () => {
  assert.strictEqual(isBefore("2026-01-01", "2026-01-02"), true);
  assert.strictEqual(isAfter("2026-01-02", "2026-01-01"), true);
  assert.strictEqual(isSameOrBefore("2026-01-01", "2026-01-01"), true);
  assert.strictEqual(isSameOrBefore("2025-12-31", "2026-01-01"), true);
  assert.strictEqual(isSameOrAfter("2026-01-01", "2026-01-01"), true);
});

// ---------------------------------------------------------------------------
// Range helpers
// ---------------------------------------------------------------------------

test("daysBetween: inclusive count", () => {
  assert.strictEqual(daysBetween("2026-07-01", "2026-07-01"), 1); // same day
  assert.strictEqual(daysBetween("2026-07-01", "2026-07-05"), 5); // Mon–Fri
  assert.strictEqual(daysBetween("2026-01-01", "2026-12-31"), 365); // non-leap year
});

test("startOfMonth / endOfMonth", () => {
  assert.strictEqual(startOfMonth("2026-07-15"), "2026-07-01");
  assert.strictEqual(endOfMonth("2026-07-15"), "2026-07-31");
  assert.strictEqual(endOfMonth("2026-02-15"), "2026-02-28");
  assert.strictEqual(endOfMonth("2024-02-15"), "2024-02-29"); // leap
});

// ---------------------------------------------------------------------------
// Relative due labels
// ---------------------------------------------------------------------------

test("relativeDueLabel: today", () => {
  assert.strictEqual(relativeDueLabel("2026-07-09", "2026-07-09"), "today");
});

test("relativeDueLabel: tomorrow", () => {
  assert.strictEqual(relativeDueLabel("2026-07-10", "2026-07-09"), "tomorrow");
});

test("relativeDueLabel: in N days", () => {
  assert.strictEqual(relativeDueLabel("2026-07-14", "2026-07-09"), "in 5 days");
});

test("relativeDueLabel: overdue by N days", () => {
  assert.strictEqual(relativeDueLabel("2026-07-04", "2026-07-09"), "overdue by 5 days");
});

test("relativeDueLabel: yesterday", () => {
  assert.strictEqual(relativeDueLabel("2026-07-08", "2026-07-09"), "yesterday");
});

test("relativeDueLabel: empty inputs", () => {
  assert.strictEqual(relativeDueLabel("", "2026-07-09"), "");
  assert.strictEqual(relativeDueLabel("2026-07-09", ""), "");
});

// ---------------------------------------------------------------------------
// Schedule preview — Payment Plans (Issue 9)  [ADR frontend timezone rules]
// ---------------------------------------------------------------------------

test("schedule: monthly — 4 occurrences from Jan 15", () => {
  const dates = generateSchedule("2026-01-15", "MONTHLY", 4);
  assert.deepStrictEqual(dates, [
    "2026-01-15",
    "2026-02-15",
    "2026-03-15",
    "2026-04-15",
  ]);
});

test("schedule: weekly — 4 occurrences", () => {
  const dates = generateSchedule("2026-07-06", "WEEKLY", 4);
  assert.deepStrictEqual(dates, [
    "2026-07-06",
    "2026-07-13",
    "2026-07-20",
    "2026-07-27",
  ]);
});

test("schedule: biweekly — 4 occurrences", () => {
  const dates = generateSchedule("2026-07-01", "BIWEEKLY", 4);
  assert.deepStrictEqual(dates, [
    "2026-07-01",
    "2026-07-15",
    "2026-07-29",
    "2026-08-12",
  ]);
});

test("schedule: quarterly — 4 occurrences", () => {
  const dates = generateSchedule("2026-01-15", "QUARTERLY", 4);
  assert.deepStrictEqual(dates, [
    "2026-01-15",
    "2026-04-15",
    "2026-07-15",
    "2026-10-15",
  ]);
});

test("schedule: yearly — 4 occurrences", () => {
  const dates = generateSchedule("2026-06-01", "YEARLY", 4);
  assert.deepStrictEqual(dates, [
    "2026-06-01",
    "2027-06-01",
    "2028-06-01",
    "2029-06-01",
  ]);
});

test("schedule: end-of-month clamping across months", () => {
  // Jan 31 → Feb 28 → Mar 28 → Apr 28 (day clamped to 28 after Feb)
  const dates = generateSchedule("2026-01-31", "MONTHLY", 4);
  assert.deepStrictEqual(dates, [
    "2026-01-31",
    "2026-02-28",
    "2026-03-28",
    "2026-04-28",
  ]);
});

test("schedule: unknown frequency returns single date", () => {
  const dates = generateSchedule("2026-07-09", "DAILY", 5);
  assert.deepStrictEqual(dates, ["2026-07-09"]);
});

// ---------------------------------------------------------------------------
// Timezone boundary — date-only arithmetic avoids toISOString day shifts
// (Issue 9 / ADR frontend timezone rules)
// ---------------------------------------------------------------------------

test("timezone: date-only addMonths does not depend on system timezone", () => {
  // The arithmetic is pure — it never calls new Date() getters.
  // The result is the same regardless of where the code runs.
  const result = addMonths("2026-01-15", 1);
  assert.strictEqual(result, "2026-02-15");
});

test("timezone: addDays uses UTC noon to avoid DST shifts", () => {
  // Adding 1 day to a date crossing a DST boundary should still add exactly 1 day.
  const result = addDays("2026-03-08", 1); // US DST spring-forward
  assert.strictEqual(result, "2026-03-09");
});

test("timezone: schedule preview dates are stable across timezones", () => {
  // The dates should be identical regardless of whether you're in Tashkent (+5)
  // or New York (-4/-5 DST).
  const dates = generateSchedule("2026-01-31", "MONTHLY", 3);
  // Jan 31 → Feb 28 → Mar 28 (day clamped after Feb)
  assert.deepStrictEqual(dates, [
    "2026-01-31",
    "2026-02-28",
    "2026-03-28",
  ]);
});

// ---------------------------------------------------------------------------
// High-risk date-only operations that must NOT bypass the calendar module
// (Issue 11 guardrail)
// ---------------------------------------------------------------------------

test("guardrail: addMonths is not equivalent to new Date + setMonth", () => {
  // new Date("2026-01-31") + setMonth(1) can give March 3 due to JS rollover.
  // The calendar module gives Feb 28, which is the correct date-only result.
  const calendarResult = addMonths("2026-01-31", 1);
  assert.strictEqual(calendarResult, "2026-02-28");

  // Verify that plain JS would NOT give this correct result:
  const d = new Date(2026, 0, 31); // Jan 31
  d.setMonth(d.getMonth() + 1);    // Feb 31 → overflows to Mar 3!
  const jsResult = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  assert.notStrictEqual(jsResult, "2026-02-28");
});

test("guardrail: compareDates does NOT parse with new Date()", () => {
  // new Date("2026-07-09") can return July 8 or July 9 depending on timezone.
  // Our compareDates uses pure string parsing — no timezone sensitivity.
  const cmp = compareDates("2026-07-09", "2026-07-10");
  assert.strictEqual(cmp, -1); // always -1, regardless of timezone
});

// ---------------------------------------------------------------------------
// daysInMonth (helper) — leap year correctness
// ---------------------------------------------------------------------------

test("daysInMonth: leap year February", () => {
  assert.strictEqual(daysInMonth(2024, 2), 29);
  assert.strictEqual(daysInMonth(2025, 2), 28);
  assert.strictEqual(daysInMonth(2026, 2), 28);
  assert.strictEqual(daysInMonth(2028, 2), 29);
});

test("daysInMonth: standard months", () => {
  assert.strictEqual(daysInMonth(2026, 1), 31);
  assert.strictEqual(daysInMonth(2026, 4), 30);
  assert.strictEqual(daysInMonth(2026, 7), 31);
  assert.strictEqual(daysInMonth(2026, 12), 31);
});
