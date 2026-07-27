export type CubicBezier = readonly [number, number, number, number];

export const motion = {
  duration: {
    feedback: 100,
    fast: 150,
    standard: 240,
    slow: 400,
  },
  easing: {
    standard: [0.2, 0, 0, 1] as CubicBezier,
    enter: [0, 0, 0, 1] as CubicBezier,
    exit: [0.3, 0, 1, 1] as CubicBezier,
    linear: [0, 0, 1, 1] as CubicBezier,
  },
} as const;
