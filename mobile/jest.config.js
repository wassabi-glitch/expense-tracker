const expoPreset = require('jest-expo/jest-preset');

/** @type {import('jest').Config} */
module.exports = {
  ...expoPreset,
  clearMocks: true,
  restoreMocks: true,
  resolver: '<rootDir>/tests/jest-resolver.js',
  transform: {
    ...expoPreset.transform,
    '^.+\\.mjs$': ['babel-jest', { presets: ['babel-preset-expo'] }],
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(.pnpm|react-native|@react-native|@react-native-community|expo|@expo|@expo-google-fonts|react-navigation|@react-navigation|@sentry/react-native|native-base|standard-navigation|msw|@mswjs|@open-draft|until-async|rettime|heroui-native|lucide-react-native))',
    '/node_modules/react-native-reanimated/plugin/',
    '/node_modules/@react-native/babel-preset/',
  ],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  moduleNameMapper: {
    '^@/assets/(.*)$': '<rootDir>/assets/$1',
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.expo/',
    '<rootDir>/.maestro/',
  ],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.web.{ts,tsx}',
    '!src/**/index.ts',
    '!src/test/**',
  ],
  coverageDirectory: '<rootDir>/coverage',
  coverageReporters: ['text', 'lcov', 'json-summary'],
  // Earned baseline ratchet. Raise these values as product slices add tests;
  // lowering them requires an explicit review decision.
  coverageThreshold: {
    global: {
      branches: 34,
      functions: 27,
      lines: 40,
      statements: 39,
    },
  },
};
