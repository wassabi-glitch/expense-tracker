/**
 * User-Local Calendar Module (ADR frontend timezone rules).
 *
 * Owns date-only parsing, arithmetic, comparison, schedule preview, and
 * relative-due-label behaviour for user-facing frontend dates.
 *
 * Every public function takes and returns **date-only strings** in
 * ``YYYY-MM-DD`` format.  No ``Date`` object is constructed internally
 * except to resolve "today" in a specific IANA timezone via
 * ``Intl.DateTimeFormat``.  This avoids the ``toISOString`` day-shift bug
 * and keeps the module pure for the date-only use-cases the UI needs.
 *
 * Operations that do NOT belong here:
 *   - Display formatting (use ``format.js``)
 *   - Technical / audit timestamps (use raw ``Date`` / ``dayjs``)
 *   - UTC datetime arithmetic
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** @returns {number} Days in the given month (1-indexed). */
function daysInMonth(year, month) {
  // month is 1-12
  return new Date(Date.UTC(year, month, 0)).getUTCDate();
}

/**
 * Clamp `day` so it does not exceed the last day of `year`-`month`.
 * e.g. Jan 31 + 1 month → Feb 28 (or 29).
 */
function clampDay(year, month, day) {
  const max = daysInMonth(year, month);
  return day > max ? max : day;
}

// ---------------------------------------------------------------------------
// Parse / format
// ---------------------------------------------------------------------------

/**
 * Parse a ``YYYY-MM-DD`` string into a plain object.
 * Returns ``null`` for unparseable input.
 *
 * @param {string} dateString
 * @returns {{year: number, month: number, day: number} | null}
 */
export function parseDateString(dateString) {
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

/**
 * Format a {year, month, day} object back to ``YYYY-MM-DD``.
 *
 * @param {{year: number, month: number, day: number}} obj
 * @returns {string}
 */
export function toDateString(year, month, day) {
  const y = String(year).padStart(4, "0");
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// ---------------------------------------------------------------------------
// Today
// ---------------------------------------------------------------------------

/**
 * Return today's date as ``YYYY-MM-DD`` in the given IANA timezone.
 * Falls back to the system local date when ``timeZone`` is omitted.
 *
 * Uses ``Intl.DateTimeFormat`` — no ``Date`` getter calls that would
 * reflect the system timezone when we asked for a different one.
 */
export function todayInZone(timeZone) {
  try {
    const fmt = new Intl.DateTimeFormat("en-CA", {
      timeZone: timeZone || undefined,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return fmt.format(new Date()); // "YYYY-MM-DD" in the target zone
  } catch {
    // Fallback: system local date
    const d = new Date();
    return toDateString(d.getFullYear(), d.getMonth() + 1, d.getDate());
  }
}

// ---------------------------------------------------------------------------
// Arithmetic
// ---------------------------------------------------------------------------

/** Add ``n`` days (negative = subtract). */
export function addDays(dateString, n) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  // Use UTC noon to avoid DST shifts
  const d = new Date(Date.UTC(parsed.year, parsed.month - 1, parsed.day, 12, 0, 0));
  d.setUTCDate(d.getUTCDate() + Number(n));
  return toDateString(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
}

/** Add ``n`` weeks (7 days per week). */
export function addWeeks(dateString, n) {
  return addDays(dateString, Number(n) * 7);
}

/** Add ``n`` calendar months.  The day is clamped to the last day of the
 *  target month (e.g. Jan 31 → Feb 28). */
export function addMonths(dateString, n) {
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

/** Add ``n`` quarters (3 months each). */
export function addQuarters(dateString, n) {
  return addMonths(dateString, Number(n) * 3);
}

/** Add ``n`` years.  Feb 29 stays Feb 29 only in leap years; otherwise
 *  clamped to Feb 28. */
export function addYears(dateString, n) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  const year = parsed.year + Number(n);
  const day = clampDay(year, parsed.month, parsed.day);
  return toDateString(year, parsed.month, day);
}

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

/**
 * Compare two ``YYYY-MM-DD`` strings.
 * @returns {number} -1 (a < b), 0 (equal), 1 (a > b), or null if either is invalid.
 */
export function compareDates(a, b) {
  if (a === b) return 0;
  const pa = parseDateString(a);
  const pb = parseDateString(b);
  if (!pa || !pb) return null;
  if (pa.year !== pb.year) return pa.year < pb.year ? -1 : 1;
  if (pa.month !== pb.month) return pa.month < pb.month ? -1 : 1;
  if (pa.day !== pb.day) return pa.day < pb.day ? -1 : 1;
  return 0;
}

export function isBefore(a, b) {
  return compareDates(a, b) === -1;
}

export function isAfter(a, b) {
  return compareDates(a, b) === 1;
}

export function isSameOrBefore(a, b) {
  const cmp = compareDates(a, b);
  return cmp === -1 || cmp === 0;
}

export function isSameOrAfter(a, b) {
  const cmp = compareDates(a, b);
  return cmp === 1 || cmp === 0;
}

// ---------------------------------------------------------------------------
// Range helpers
// ---------------------------------------------------------------------------

/** Number of calendar days between two dates (inclusive of both ends). */
export function daysBetween(a, b) {
  const pa = parseDateString(a);
  const pb = parseDateString(b);
  if (!pa || !pb) return 0;
  const da = new Date(Date.UTC(pa.year, pa.month - 1, pa.day, 12, 0, 0));
  const db = new Date(Date.UTC(pb.year, pb.month - 1, pb.day, 12, 0, 0));
  return Math.abs(Math.round((db - da) / 86400000)) + 1;
}

/** First day of the month containing ``dateString``. */
export function startOfMonth(dateString) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  return toDateString(parsed.year, parsed.month, 1);
}

/** Last day of the month containing ``dateString``. */
export function endOfMonth(dateString) {
  const parsed = parseDateString(dateString);
  if (!parsed) return dateString;
  return toDateString(parsed.year, parsed.month, daysInMonth(parsed.year, parsed.month));
}

// ---------------------------------------------------------------------------
// Relative due labels
// ---------------------------------------------------------------------------

/**
 * Return a human-readable relative label comparing ``dueDate`` to
 * ``todayDate`` (both ``YYYY-MM-DD``).
 *
 * @returns {string} e.g. "today", "tomorrow", "in 3 days", "overdue by 5 days"
 */
export function relativeDueLabel(dueDate, todayDate) {
  if (!dueDate || !todayDate) return "";
  const cmp = compareDates(dueDate, todayDate);
  if (cmp === null) return "";
  if (cmp === 0) return "today";
  const days = daysBetween(dueDate, todayDate) - 1; // exclusive
  if (cmp > 0) {
    // dueDate is in the future
    if (days === 1) return "tomorrow";
    return `in ${days} days`;
  }
  // dueDate is in the past
  if (days === 1) return "yesterday";
  return `overdue by ${days} days`;
}

// ---------------------------------------------------------------------------
// Schedule preview (Payment Plans)
// ---------------------------------------------------------------------------

/** Supported schedule frequencies. */
export const SCHEDULE_FREQUENCIES = [
  "WEEKLY",
  "BIWEEKLY",
  "MONTHLY",
  "QUARTERLY",
  "YEARLY",
];

const FREQUENCY_ADD = {
  WEEKLY: (d, _n) => addWeeks(d, 1),
  BIWEEKLY: (d, _n) => addWeeks(d, 2),
  MONTHLY: (d, _n) => addMonths(d, 1),
  QUARTERLY: (d, _n) => addQuarters(d, 1),
  YEARLY: (d, _n) => addYears(d, 1),
};

/**
 * Generate a schedule of ``count`` due dates starting from ``startDate``
 * (``YYYY-MM-DD``) at the given ``frequency``.
 *
 * The first date is the start date itself.  Every subsequent date is
 * computed by adding one frequency interval to the previous date using
 * pure date-only arithmetic — no ``Date`` timezone shifts.
 *
 * @param {string} startDate  ``YYYY-MM-DD``
 * @param {string} frequency  One of ``SCHEDULE_FREQUENCIES``
 * @param {number} count      Number of occurrences (≥ 1)
 * @returns {string[]}
 */
export function generateSchedule(startDate, frequency, count) {
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
