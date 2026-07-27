import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import { Button } from '@/components/ui/button';
import { Settings2, X } from 'lucide-react-native';

import i18next from '@/i18n';
import { authPresentationColors, darkColors, radii, sizes, spacing, typography } from '@/theme';

import { SignInScreen } from '../screens/sign-in-screen';
import { SignUpScreen } from '../screens/sign-up-screen';
import { CheckEmailScreen } from '../screens/check-email-screen';
import { VerifyAccountScreen } from '../screens/verify-account-screen';
import { ForgotPasswordScreen } from '../screens/forgot-password-screen';
import { ResetPasswordScreen } from '../screens/reset-password-screen';
import { 
  authPreviewFixtures, 
  authPreviewSignInFixtures,
  authPreviewCheckEmailFixtures,
  authPreviewVerifyAccountFixtures,
  authPreviewForgotPasswordFixtures,
  authPreviewResetPasswordFixtures,
  authPreviewChangePasswordFixtures
} from './auth-preview-fixtures';
import { ChangePasswordForm } from '../../settings/components/change-password-form';
const ChevronLeft = (props: any) => <Text>{'<'}</Text>; const ChevronRight = (props: any) => <Text>{'>'}</Text>;

const previewLanguages = ['en', 'ru', 'uz'] as const;
type ScreenType = 'signUp' | 'signIn' | 'checkEmail' | 'verifyAccount' | 'forgotPassword' | 'resetPassword' | 'changePassword';

/** Development-only adapter; production auth presentation remains in SignUpScreen. */
export function AuthPreviewScreen() {
  const { t } = useTranslation();
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('signUp');
  const [fixtureIndex, setFixtureIndex] = useState(0);
  const [isToolbarVisible, setIsToolbarVisible] = useState(true);

  let fixtures: readonly any[];
  switch (currentScreen) {
    case 'signUp': fixtures = authPreviewFixtures; break;
    case 'signIn': fixtures = authPreviewSignInFixtures; break;
    case 'checkEmail': fixtures = authPreviewCheckEmailFixtures; break;
    case 'verifyAccount': fixtures = authPreviewVerifyAccountFixtures; break;
    case 'forgotPassword': fixtures = authPreviewForgotPasswordFixtures; break;
    case 'resetPassword': fixtures = authPreviewResetPasswordFixtures; break;
    case 'changePassword': fixtures = authPreviewChangePasswordFixtures; break;
  }
  
  const fixture = fixtures[fixtureIndex] ?? fixtures[0];

  function moveFixture(offset: number) {
    setFixtureIndex((current) =>
      (current + offset + fixtures.length) % fixtures.length,
    );
  }

  function handleSwitchScreen(screen: ScreenType) {
    setCurrentScreen(screen);
    setFixtureIndex(0);
  }

  return (
    <View className="flex-1" style={styles.root}>
      {currentScreen === 'signUp' && (
        <SignUpScreen
          key={fixture.id}
          {...fixture.screenProps}
          onSignInPress={() => handleSwitchScreen('signIn')}
          onCreateAccountPress={() => handleSwitchScreen('checkEmail')}
        />
      )}
      {currentScreen === 'signIn' && (
        <SignInScreen
          key={fixture.id}
          {...fixture.screenProps}
          onCreateAccountPress={() => handleSwitchScreen('signUp')}
        />
      )}
      {currentScreen === 'checkEmail' && (
        <CheckEmailScreen
          key={fixture.id}
          {...fixture.screenProps}
          onBackToSignInPress={() => handleSwitchScreen('signIn')}
        />
      )}
      {currentScreen === 'verifyAccount' && (
        <VerifyAccountScreen
          key={fixture.id}
          {...fixture.screenProps}
          onContinueToSignInPress={() => handleSwitchScreen('signIn')}
          onRequestNewLinkPress={() => handleSwitchScreen('checkEmail')}
        />
      )}
      {currentScreen === 'forgotPassword' && (
        <ForgotPasswordScreen
          key={fixture.id}
          {...fixture.screenProps}
          onBackToSignInPress={() => handleSwitchScreen('signIn')}
        />
      )}
      {currentScreen === 'resetPassword' && (
        <ResetPasswordScreen
          key={fixture.id}
          {...fixture.screenProps}
        />
      )}
      {currentScreen === 'changePassword' && (
        <View style={{ flex: 1, padding: 16, paddingTop: 64 }}>
          <ChangePasswordForm
            key={fixture.id}
            {...fixture.screenProps}
            onSubmitOverride={() => {}}
          />
        </View>
      )}

      {!isToolbarVisible ? (
        <Button
          className="absolute bottom-3 right-3"
          isIconOnly
          onPress={() => setIsToolbarVisible(true)}
          size="sm"
          style={styles.toolbar}
          variant="ghost"
        >
          <Settings2 color={darkColors.textPrimary} size={sizes.button.icon} />
        </Button>
      ) : (
        <View
          accessibilityLabel={t('auth.preview.galleryLabel')}
          className="absolute bottom-3 left-3 right-3 gap-2"
          style={styles.toolbar}
          testID="auth-preview-toolbar"
        >
          <View className="absolute right-0 top-0 z-10">
            <Button
              isIconOnly
              onPress={() => setIsToolbarVisible(false)}
              size="sm"
              variant="ghost"
            >
              <X color={darkColors.textPrimary} size={sizes.button.icon} />
            </Button>
          </View>
          
          <View className="flex-row items-center justify-between gap-2 px-6">
            <Button
              accessibilityLabel={t('auth.preview.previousState')}
              isIconOnly
              onPress={() => moveFixture(-1)}
              size="sm"
              variant="ghost"
            >
              <ChevronLeft color={darkColors.textPrimary} size={sizes.button.icon} />
            </Button>
            <Text numberOfLines={2} style={[typography.supporting, styles.stateLabel]}>
              {t(fixture.labelKey)}
            </Text>
            <Button
              accessibilityLabel={t('auth.preview.nextState')}
              isIconOnly
              onPress={() => moveFixture(1)}
              size="sm"
              variant="ghost"
            >
              <ChevronRight color={darkColors.textPrimary} size={sizes.button.icon} />
            </Button>
          </View>

          <View className="flex-row justify-center gap-1 flex-wrap mb-1">
            <Button size="sm" variant={currentScreen === 'signUp' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('signUp')}>Up</Button>
            <Button size="sm" variant={currentScreen === 'signIn' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('signIn')}>In</Button>
            <Button size="sm" variant={currentScreen === 'checkEmail' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('checkEmail')}>Email</Button>
            <Button size="sm" variant={currentScreen === 'verifyAccount' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('verifyAccount')}>Verify</Button>
            <Button size="sm" variant={currentScreen === 'forgotPassword' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('forgotPassword')}>ForgotPwd</Button>
            <Button size="sm" variant={currentScreen === 'resetPassword' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('resetPassword')}>ResetPwd</Button>
            <Button size="sm" variant={currentScreen === 'changePassword' ? 'primary' : 'ghost'} onPress={() => handleSwitchScreen('changePassword')}>ChangePwd</Button>
          </View>

          <View
            accessibilityLabel={t('auth.preview.chooseLanguage')}
            className="flex-row justify-center gap-2"
          >
            {previewLanguages.map((language) => (
              <Button
                accessibilityLabel={language.toUpperCase()}
                key={language}
                onPress={() => void i18next.changeLanguage(language)}
                size="sm"
                variant={i18next.resolvedLanguage === language ? 'primary' : 'ghost'}
              >
                {language.toUpperCase()}
              </Button>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: authPresentationColors.canvas,
  },
  toolbar: {
    alignSelf: 'center',
    backgroundColor: darkColors.surface,
    borderColor: darkColors.borderSubtle,
    borderRadius: radii.large,
    borderWidth: 1,
    maxWidth: 420,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  stateLabel: {
    color: darkColors.textPrimary,
    flex: 1,
    textAlign: 'center',
  },
});
