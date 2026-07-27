type TranslationTree = {
  readonly [key: string]: string | TranslationTree;
};

function collectLeafKeys(
  tree: TranslationTree,
  prefix = '',
): string[] {
  return Object.entries(tree).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;

    return typeof value === 'string'
      ? [path]
      : collectLeafKeys(value, path);
  });
}

export function assertLocaleKeyParity(
  locales: Readonly<Record<string, TranslationTree>>,
  referenceLocale = 'en',
) {
  const reference = locales[referenceLocale];

  if (!reference) {
    throw new Error(`Reference locale "${referenceLocale}" is missing.`);
  }

  const expectedKeys = collectLeafKeys(reference).sort();

  for (const [locale, translations] of Object.entries(locales)) {
    const actualKeys = collectLeafKeys(translations).sort();

    if (actualKeys.join('\n') !== expectedKeys.join('\n')) {
      const missing = expectedKeys.filter((key) => !actualKeys.includes(key));
      const unexpected = actualKeys.filter((key) => !expectedKeys.includes(key));

      throw new Error(
        `Locale "${locale}" does not match "${referenceLocale}". ` +
          `Missing: ${missing.join(', ') || 'none'}. ` +
          `Unexpected: ${unexpected.join(', ') || 'none'}.`,
      );
    }
  }
}
