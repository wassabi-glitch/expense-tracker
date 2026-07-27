# Sarflog Mobile

Sarflog's React Native application uses Expo SDK 57, Expo Router, and Node 22.13 or newer.

## Get started

1. Install dependencies

   ```bash
   npm ci
   ```

2. Start the app

   ```bash
   npx expo start
   ```

In the output, you'll find options to open the app in a

- [development build](https://docs.expo.dev/develop/development-builds/introduction/)
- [Android emulator](https://docs.expo.dev/workflow/android-studio-emulator/)
- [iOS simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Expo Go](https://expo.dev/go), a limited sandbox for trying out app development with Expo

Application routes live in `src/app`. This project uses [file-based routing](https://docs.expo.dev/router/introduction).

## Required quality gate

Run this before handing off or committing a mobile product slice:

```bash
npm run verify
```

It validates Expo dependency compatibility, TypeScript, ESLint and test rules, the shared layout policy, Jest/component/router/API tests, and the coverage ratchet.

Focused commands:

```bash
npm test -- path/to/file.test.ts
npm run test:watch
npm run test:coverage
npm run typecheck
npm run lint
```

Jest uses `jest-expo`, React Native Testing Library, Expo Router's testing library, and MSW. Unhandled HTTP requests fail tests; automated tests must never contact FastAPI, Resend, or another external service. Native smoke and release-critical flows live in `.maestro/` and run against Android and iOS builds through `.eas/workflows/e2e-tests.yml`.

## Get a fresh project

When you're ready, run:

```bash
npm run reset-project
```

This command will move the starter code to the **app-example** directory and create a blank **app** directory where you can start developing.

### Other setup steps

- To set up ESLint for linting, run `npx expo lint`, or follow our guide on ["Using ESLint and Prettier"](https://docs.expo.dev/guides/using-eslint/)
- Unit, component, router, HTTP-boundary, and native E2E testing are already configured; do not replace them with snapshot-only coverage.
- Learn more about the TypeScript setup in this template in our guide on ["Using TypeScript"](https://docs.expo.dev/guides/typescript/)

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.
