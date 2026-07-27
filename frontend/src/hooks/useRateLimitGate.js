import { useState, useRef, useEffect, useCallback } from "react";

/**
 * Opaque rate-limit gate for auth forms.
 *
 * When the backend returns 429 + a Retry-After header, the API client
 * attaches `retryAfterSeconds` to the error object (see client.js toApiError).
 * This hook reads that value, disables the submit button, and silently
 * re-enables it after the cooldown expires — without exposing a countdown
 * to the user (per the Issue 3 security model).
 *
 * @param {object} [opts]
 * @param {() => void} [opts.onExpire] — called when the rate-limit timer expires
 * @returns {{ isRateLimited: boolean, onRateLimitError: (error: any) => void }}
 */
export function useRateLimitGate(opts = {}) {
  const { onExpire } = opts;
  const [isRateLimited, setIsRateLimited] = useState(false);
  const timerRef = useRef(null);
  const onExpireRef = useRef(onExpire);

  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const onRateLimitError = useCallback(
    (error) => {
      const seconds = error?.retryAfterSeconds;
      if (!seconds || seconds <= 0) return;
      setIsRateLimited(true);
      clearTimer();
      timerRef.current = setTimeout(() => {
        setIsRateLimited(false);
        timerRef.current = null;
        onExpireRef.current?.();
      }, seconds * 1000);
    },
    [clearTimer],
  );

  useEffect(() => {
    return clearTimer;
  }, [clearTimer]);

  return { isRateLimited, onRateLimitError };
}
