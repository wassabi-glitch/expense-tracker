import { en } from './en';
import { ru } from './ru';
import { uz } from './uz';

export const locales = { en, ru, uz } as const;

export type Locale = keyof typeof locales;

export type TranslationKeys = typeof en;
