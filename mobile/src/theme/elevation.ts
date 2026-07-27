/**
 * Semantic depth identifiers shared by Android and iOS.
 * Platform-specific shadow recipes remain intentionally deferred until the
 * component gallery can be checked on real devices.
 */
export const depth = {
  flat: 'flat',
  subtle: 'subtle',
  raised: 'raised',
  overlay: 'overlay',
} as const;

export type DepthLevel = keyof typeof depth;
