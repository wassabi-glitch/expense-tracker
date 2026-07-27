import { assertLocaleKeyParity } from './locale-parity';
import { locales } from '../../src/i18n/locales';

test('keeps every real mobile locale in exact key parity', () => {
  expect(() => assertLocaleKeyParity(locales)).not.toThrow();
});

test('accepts matching nested translation keys', () => {
  expect(() =>
    assertLocaleKeyParity({
      en: { auth: { submit: 'Continue', errors: { offline: 'Offline' } } },
      ru: { auth: { submit: 'Продолжить', errors: { offline: 'Нет сети' } } },
      uz: { auth: { submit: 'Davom etish', errors: { offline: 'Oflayn' } } },
    }),
  ).not.toThrow();
});

test('reports missing and unexpected translation keys', () => {
  expect(() =>
    assertLocaleKeyParity({
      en: { auth: { submit: 'Continue', offline: 'Offline' } },
      ru: { auth: { submit: 'Продолжить', retry: 'Повторить' } },
      uz: { auth: { submit: 'Davom etish', offline: 'Oflayn' } },
    }),
  ).toThrow(
    'Locale "ru" does not match "en". Missing: auth.offline. Unexpected: auth.retry.',
  );
});
