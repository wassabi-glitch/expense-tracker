# Source Architecture

Sarflog mobile uses a feature-first structure. Expo Router owns navigation, feature modules own product behavior, and shared infrastructure stays independent of product features.

## Directory responsibilities

```text
src/
├── app/                 Expo Router routes and layouts only
├── components/
│   ├── ui/              Thin Sarflog wrappers around HeroUI only when needed
│   └── shared/          Reusable Sarflog components used by multiple features
├── features/            Product modules such as auth, dashboard, and expenses
├── hooks/               Truly application-wide hooks only
├── layout/              Responsive window classes, content caps, and adaptive layout hooks
├── lib/                 API, authentication, query, and other infrastructure
├── providers/           Root React providers composed by app/_layout.tsx
├── theme/               Colors, spacing, typography, radii, and shadows
└── types/               Types shared by multiple otherwise-independent features
```

## Feature module shape

Create subdirectories only when a feature actually needs them:

```text
features/expenses/
├── api/                 Expense endpoint functions
├── components/          Expense-only UI
├── hooks/               Expense queries, mutations, and UI hooks
├── schemas/             Expense form validation
└── screens/             Screen-level feature composition
```

## Dependency rules

- Route files should stay thin and render a feature screen.
- Features may import from `components`, `layout`, `lib`, `theme`, and `types`.
- HeroUI Native is the default component layer; `components/ui` wrappers must stay thin and must not import from a product feature.
- API records belong in TanStack Query, not duplicated in a client-state store.
- Authentication secrets belong in Expo SecureStore.
- User-facing dates must use the user's effective timezone and API requests must send `X-Timezone`.
- Add a new abstraction only after a concrete use case exists.

Use the existing `@/` alias for imports from `src`.
