import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Switch,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';
import { getRefreshToken } from '@/lib/auth/secure-store';
import { useNativeLogoutMutation, useNativeLogoutAllMutation } from '@/features/auth/api/auth-mutations';
import { useTheme } from '@/hooks/use-theme';
import { GoogleSignin } from '@react-native-google-signin/google-signin';

import { useUserQuery } from '../../auth/hooks/use-user-query';
import { ChangePasswordForm } from '../components/change-password-form';
import { useAppLockStore } from '@/features/app-lock/hooks/use-app-lock';

export function SettingsScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { signOut, signOutAll } = useAuthStore();
  const { colors } = useTheme();

  const userQuery = useUserQuery();
  const hasLocalPassword = userQuery.data?.has_local_password;

  const logoutMutation = useNativeLogoutMutation();
  const logoutAllMutation = useNativeLogoutAllMutation();

  // App Lock state
  const {
    pinExists,
    bioEnabled,
    bioAvailable,
    isInitialized,
    appLockEnabled,
    enableBio,
    disableBio,
    toggleAppLock,
    startChangePin,
  } = useAppLockStore();

  const [error, setError] = useState<string | null>(null);

  const performGoogleSignOut = async () => {
    try {
      GoogleSignin.configure({
        webClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
        offlineAccess: true,
      });
      await GoogleSignin.signOut();
    } catch (e) {
      // Ignored: user might not be signed in with Google
    }
  };

  const handleLogout = async () => {
    setError(null);
    try {
      const refreshToken = await getRefreshToken();
      if (refreshToken) {
        await logoutMutation.mutateAsync({ refresh_token: refreshToken });
      }
      await performGoogleSignOut();
      await signOut();
      router.replace('/sign-in');
    } catch (e: any) {
      setError(t('settings.signOutFailed'));
      await performGoogleSignOut();
      await signOut();
      router.replace('/sign-in');
    }
  };

  const handleLogoutAll = async () => {
    setError(null);
    try {
      await logoutAllMutation.mutateAsync();
      await performGoogleSignOut();
      await signOutAll();
      router.replace('/sign-in');
    } catch (e: any) {
      setError(t('settings.signOutAllFailed'));
      await performGoogleSignOut();
      await signOutAll();
      router.replace('/sign-in');
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.screen }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>{t('settings.title')}</Text>

        {error && <Text style={styles.errorText}>{error}</Text>}

        {/* ── App Lock Section ── */}
        {isInitialized && (
          <View style={[styles.appLockSection, { backgroundColor: colors.surface }]}>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>
              {t('appLock.settings.appLockToggle')}
            </Text>
            <Text style={[styles.sectionDesc, { color: colors.textSecondary }]}>
              {t('appLock.settings.toggleDesc')}
            </Text>

            {/* 1. Master toggle — enable/disable entire App Lock */}
            <View style={styles.appLockRow}>
              <Text style={{ color: colors.textPrimary, flex: 1 }}>
                {appLockEnabled
                  ? t('appLock.settings.appLockOn')
                  : t('appLock.settings.appLockOff')}
              </Text>
              <Switch
                value={appLockEnabled}
                onValueChange={(enabled) => toggleAppLock(enabled)}
                trackColor={{ false: colors.borderControl, true: colors.brand.action }}
              />
            </View>

            {/* 2. Biometric toggle */}
            {bioAvailable && (
              <View style={styles.appLockRow}>
                <Text
                  style={{
                    color: appLockEnabled ? colors.textPrimary : colors.textSecondary,
                    flex: 1,
                  }}
                >
                  {t('appLock.settings.biometricToggle')}
                </Text>
                <Switch
                  value={bioEnabled}
                  disabled={!appLockEnabled}
                  onValueChange={(enabled) => {
                    if (enabled) {
                      enableBio();
                    } else {
                      disableBio();
                    }
                  }}
                  trackColor={{
                    false: appLockEnabled ? colors.borderControl : colors.borderSubtle,
                    true: appLockEnabled ? colors.brand.action : colors.borderSubtle,
                  }}
                />
              </View>
            )}

            {/* 3. Change PIN — only visible when App Lock is ON and PIN exists */}
            {appLockEnabled && pinExists && (
              <TouchableOpacity
                style={[styles.changePinButton, { borderColor: colors.borderControl }]}
                onPress={() => startChangePin()}
              >
                <Text style={[styles.changePinText, { color: colors.textPrimary }]}>
                  {t('appLock.settings.changePin')}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {userQuery.isLoading ? (
          <ActivityIndicator size="large" color={colors.textPrimary} style={{ marginVertical: 24 }} />
        ) : hasLocalPassword ? (
          <ChangePasswordForm />
        ) : (
          <View style={[styles.noPasswordContainer, { backgroundColor: colors.surface }]}>
            <Text style={[styles.noPasswordText, { color: colors.textSecondary }]}>
              {t('settings.noLocalPassword', { defaultValue: 'You are signed in with a social account. Password changes are not applicable.' })}
            </Text>
          </View>
        )}

        <TouchableOpacity testID="btn-logout" style={styles.button} onPress={handleLogout}>
          <Text style={styles.buttonText}>{t('common.signOut')}</Text>
        </TouchableOpacity>

        <TouchableOpacity testID="btn-logout-all" style={styles.button} onPress={handleLogoutAll}>
          <Text style={styles.buttonText}>{t('settings.signOutAll')}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 32,
  },
  button: {
    backgroundColor: '#ef4444',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginBottom: 16,
    width: '100%',
    alignItems: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorText: {
    color: '#ef4444',
    marginBottom: 16,
  },
  noPasswordContainer: {
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
    alignItems: 'center',
    width: '100%',
  },
  noPasswordText: {
    fontSize: 14,
    textAlign: 'center',
  },
  appLockSection: {
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
    width: '100%',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  sectionDesc: {
    fontSize: 14,
    marginBottom: 12,
  },
  appLockRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  changePinButton: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    minHeight: 48,
    justifyContent: 'center',
  },
  changePinText: {
    fontSize: 16,
    fontWeight: '500',
  },
});
