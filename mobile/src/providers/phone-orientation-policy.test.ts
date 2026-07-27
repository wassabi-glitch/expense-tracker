import {
  largeScreenMinimumDimension,
  shouldLockPhonePortrait,
} from './phone-orientation-policy';

describe('shouldLockPhonePortrait', () => {
  test.each([
    [360, 800],
    [800, 360],
    [599, 1000],
    [1000, 599],
  ])('locks a compact %i x %i window to portrait', (width, height) => {
    expect(shouldLockPhonePortrait(width, height)).toBe(true);
  });

  test.each([
    [600, 600],
    [800, 1200],
    [1200, 800],
  ])('allows a large %i x %i window to rotate', (width, height) => {
    expect(shouldLockPhonePortrait(width, height)).toBe(false);
  });

  test('uses the Android large-screen boundary', () => {
    expect(largeScreenMinimumDimension).toBe(600);
  });
});
