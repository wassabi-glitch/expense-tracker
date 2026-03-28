import { useState, useEffect } from "react";

/**
 * Custom hook to detect screen size changes reactively.
 * @param {string} query - The media query to match (e.g., "(max-width: 768px)")
 * @returns {boolean} - Whether the query matches the current screen size.
 */
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    typeof window !== "undefined" ? window.matchMedia(query).matches : false
  );

  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQueryList = window.matchMedia(query);
    const listener = (event) => setMatches(event.matches);

    // Initial check
    setMatches(mediaQueryList.matches);

    // Add listener
    mediaQueryList.addEventListener("change", listener);
    return () => mediaQueryList.removeEventListener("change", listener);
  }, [query]);

  return matches;
}
