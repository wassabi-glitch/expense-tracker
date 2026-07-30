import '../global.css';
import '../i18n';

import { useFonts } from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { Stack } from 'expo-router';
import { HeroUINativeProvider } from 'heroui-native/provider';
import { LogBox, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import { AnimatedSplashOverlay } from '@/components/animated-icon';
import { PhoneOrientationPolicy } from '@/providers/phone-orientation-policy';
import { AppThemeProvider } from '@/providers/theme-provider';
import { fontAssets } from '@/theme';

import { AppQueryProvider } from '@/providers/query-provider';
import { AppLockProvider } from '@/providers/app-lock-provider';
import * as SystemUI from 'expo-system-ui';

void SplashScreen.preventAutoHideAsync();
SystemUI.setBackgroundColorAsync('transparent');

if (__DEV__) {
  LogBox.ignoreLogs([
    '[colorKit.RGB] An error occurred while attempting to convert',
    "Uniwind - className 'accent-field-placeholder'",
    'props.pointerEvents is deprecated',
  ]);
}

const heroUIConfig = {
  devInfo: { stylingPrinciples: false },
  textProps: { allowFontScaling: true },
  textInputProps: { allowFontScaling: true },
} as const;

import { useEffect } from 'react';
import { useRouter, useSegments } from 'expo-router';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status, restoreSession } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (status === 'restoring') {
      restoreSession();
    }
  }, [status, restoreSession]);

  useEffect(() => {
    if (status === 'restoring') return;

    // Give Expo Router a tick to mount the Layout and resolve segments
    // before attempting imperative redirects.
    const timer = setTimeout(() => {
      const inAuthGroup = segments[0] === '(auth)';
      const inPreviewGroup = segments[0] === 'auth-preview';

      if (status === 'unauthenticated' && !inAuthGroup && !inPreviewGroup) {
        router.replace('/(auth)/sign-in');
      } else if (status === 'authenticated' && inAuthGroup) {
        router.replace('/(tabs)');
      }
    }, 1);

    return () => clearTimeout(timer);
  }, [status, segments, router]);

  if (status === 'restoring') {
    return null; // Or a splash screen
  }

  return <>{children}</>;
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts(fontAssets);

  if (fontError) {
    throw fontError;
  }

  return (
    <GestureHandlerRootView style={styles.root}>
      <PhoneOrientationPolicy />
      {fontsLoaded ? (
        <AppQueryProvider>
          <AppThemeProvider>
            <HeroUINativeProvider config={heroUIConfig}>
              <AnimatedSplashOverlay />
              <AuthGuard>
                <AppLockProvider>
                  <Stack screenOptions={{ headerShown: false }}>
                    <Stack.Screen name="(tabs)" />
                    <Stack.Screen name="(auth)" />
                    <Stack.Screen name="auth-preview" />
                  </Stack>
                </AppLockProvider>
              </AuthGuard>
            </HeroUINativeProvider>
          </AppThemeProvider>
        </AppQueryProvider>
      ) : null}
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
});
