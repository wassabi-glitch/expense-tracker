// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require("eslint-config-expo/flat");
const jest = require('eslint-plugin-jest');
const testingLibrary = require('eslint-plugin-testing-library');

const testFiles = [
  '**/*.{test,spec}.{js,jsx,ts,tsx}',
  'tests/**/*.{js,jsx,ts,tsx}',
];

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['coverage/**', 'dist/**'],
  },
  {
    ...jest.configs['flat/recommended'],
    files: testFiles,
    rules: {
      ...jest.configs['flat/recommended'].rules,
      'jest/no-commented-out-tests': 'error',
      'jest/no-disabled-tests': 'error',
      'jest/no-focused-tests': 'error',
      'jest/no-identical-title': 'error',
      'jest/no-test-return-statement': 'error',
      'jest/prefer-hooks-in-order': 'error',
    },
  },
  {
    ...testingLibrary.configs['flat/react'],
    files: testFiles,
    rules: {
      ...testingLibrary.configs['flat/react'].rules,
      'testing-library/no-debugging-utils': 'error',
      'testing-library/no-wait-for-multiple-assertions': 'error',
      'testing-library/prefer-user-event': 'error',
    },
  },
]);
