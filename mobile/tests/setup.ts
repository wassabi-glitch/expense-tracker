import 'react-native-gesture-handler/jestSetup';
import '../src/i18n';
import { server } from './mocks/server';

process.env.EXPO_PUBLIC_API_URL = 'http://localhost:8000/api';

jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  Reanimated.useReducedMotion = () => false;
  return Reanimated;
});
jest.mock('react-native-worklets', () =>
  require('../node_modules/react-native-worklets/src/mock'),
);

jest.mock('uniwind', () => ({
  Uniwind: {
    setTheme: jest.fn(),
  },
  useCSSVariable: (variables: string[]) => variables.map(() => '#ffffff'),
  useResolveClassNames: () => ({}),
  useUniwind: () => ({ theme: 'dark' }),
  withUniwind: (Component: unknown) => Component,
}));

jest.mock('@/lib/toast-utils', () => ({
  showErrorToast: jest.fn(),
}));

jest.mock('react-native-webview', () => {
  const { View } = require('react-native');
  return {
    WebView: View,
  };
});

jest.mock('expo-local-authentication', () => ({
  hasHardwareAsync: jest.fn().mockResolvedValue(true),
  isEnrolledAsync: jest.fn().mockResolvedValue(true),
  authenticateAsync: jest.fn().mockResolvedValue({ success: true }),
  supportedAuthenticationTypesAsync: jest.fn().mockResolvedValue([1, 2]),
  SecurityLevel: { BIOMETRIC: 1, SECRET: 2, NONE: 0 },
}));

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
