import {
  getWindowHeightClass,
  getWindowWidthClass,
  windowBreakpoints,
} from './window-size';

describe('available-window classification', () => {
  test.each([
    [0, 'compact'],
    [599, 'compact'],
    [600, 'medium'],
    [839, 'medium'],
    [840, 'expanded'],
  ] as const)('classifies width %i as %s', (width, expected) => {
    expect(getWindowWidthClass(width)).toBe(expected);
  });

  test.each([
    [0, 'compact'],
    [479, 'compact'],
    [480, 'regular'],
  ] as const)('classifies height %i as %s', (height, expected) => {
    expect(getWindowHeightClass(height)).toBe(expected);
  });

  test('keeps the shared width boundaries explicit', () => {
    expect(windowBreakpoints.width).toEqual({ medium: 600, expanded: 840 });
  });
});
