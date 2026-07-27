import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  getWindowHeightClass,
  getWindowWidthClass,
  windowBreakpoints,
} from '../src/layout/window-size.ts';

const widthCases = [
  [0, 'compact'],
  [599, 'compact'],
  [600, 'medium'],
  [839, 'medium'],
  [840, 'expanded'],
  [1920, 'expanded'],
];

const heightCases = [
  [0, 'compact'],
  [479, 'compact'],
  [480, 'regular'],
  [1200, 'regular'],
];

for (const [width, expected] of widthCases) {
  assert.equal(getWindowWidthClass(width), expected, `width ${width}`);
}

for (const [height, expected] of heightCases) {
  assert.equal(getWindowHeightClass(height), expected, `height ${height}`);
}

const globalCss = readFileSync(new URL('../src/global.css', import.meta.url), 'utf8');
const cssBreakpoints = [
  ['medium', windowBreakpoints.width.medium],
  ['expanded', windowBreakpoints.width.expanded],
];

for (const [name, value] of cssBreakpoints) {
  assert.match(
    globalCss,
    new RegExp(`--breakpoint-${name}:\\s*${value}px;`),
    `Uniwind breakpoint ${name} must match the TypeScript source`,
  );
}

console.log('Layout breakpoint boundaries and Uniwind adapter match.');
