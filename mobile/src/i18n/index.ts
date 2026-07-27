/* eslint-disable import/no-named-as-default-member */
import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';

import { locales } from './locales';

void i18next.use(initReactI18next).init({
  resources: Object.fromEntries(
    Object.entries(locales).map(([lang, translations]) => [
      lang,
      { translation: translations },
    ]),
  ),
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
  react: {
    useSuspense: false,
  },
});

export default i18next;
