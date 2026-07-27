import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import Animated, { Easing, FadeInDown, FadeOutUp, LinearTransition } from 'react-native-reanimated';
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { StatusBar } from 'expo-status-bar';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { contentMaxWidths, useAdaptiveLayout } from '@/layout';
import {
  authPresentationColors,
  darkColors,
  motion,
  sizes,
  spacing,
  typography,
} from '@/theme';

export type AuthScreenLayoutProps = {
  title: string;
  supportingText: string;
  children: ReactNode;
  actions?: ReactNode;
  backLabel?: string;
  onBack?: () => void;
  titleRef?: React.RefObject<Text | null>;
  previewTextScale?: number;
};

export const AuthLayoutContext = createContext<{
  scrollToEnd: () => void;
} | null>(null);

export function useAuthLayout() {
  const context = useContext(AuthLayoutContext);
  if (!context) {
    return { scrollToEnd: () => { } };
  }
  return context;
}

/** Shared fixed-dark shell for every public authentication screen. */
export function AuthScreenLayout({
  title,
  supportingText,
  children,
  actions,
  backLabel,
  onBack,
  titleRef,
  previewTextScale = 1,
}: AuthScreenLayoutProps) {
  const { metrics } = useAdaptiveLayout();
  const scrollViewRef = useRef<ScrollView>(null);
  const [isKeyboardVisible, setKeyboardVisible] = useState(false);
  const [animationsReady, setAnimationsReady] = useState(false);

  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';

    const showSub = Keyboard.addListener(showEvent, () => setKeyboardVisible(true));
    const hideSub = Keyboard.addListener(hideEvent, () => setKeyboardVisible(false));

    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  useEffect(() => {
    // Delay enabling layout animations so that initial safe-area
    // and font scaling measurements aren't animated as a "falling" effect.
    const timer = setTimeout(() => {
      setAnimationsReady(true);
    }, 150);
    return () => clearTimeout(timer);
  }, []);

  return (
    <AuthLayoutContext.Provider value={{
      scrollToEnd: () => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }
    }}>
      <View className="flex-1" style={styles.canvas} testID="auth-screen-layout">
        <StatusBar style="light" />
        <LinearGradient
          colors={[
            authPresentationColors.gradient[1],
            authPresentationColors.gradient[2],
          ]}
          pointerEvents="none"
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: 0,
            height: '40%',
          }}
          testID="auth-canvas-gradient"
        />
        <View
          pointerEvents="none"
          style={StyleSheet.absoluteFill}
          testID="auth-canvas-glow"
        />

        <SafeAreaView style={{ flex: 1 }} edges={['top', 'right', 'bottom', 'left']}>
          {onBack && backLabel ? (
            <View
              className="absolute z-10"
              style={{
                top: spacing.xl,
                left: metrics.screenGutter - spacing.sm, // Subtract internal button padding so the icon visually aligns with the title
              }}
            >
              <Button
                accessibilityLabel={backLabel}
                isIconOnly
                onPress={onBack}
                size="lg"
                style={styles.backButton}
                variant="ghost"
              >
                <ArrowLeft
                  aria-hidden={true}
                  color={darkColors.textPrimary}
                  size={24}
                />
              </Button>
            </View>
          ) : null}

          <KeyboardAvoidingView
            style={{ flex: 1 }}
            behavior="padding"
          >
            <ScrollView
              ref={scrollViewRef}
              style={{ flex: 1 }}
              contentContainerStyle={[
                styles.scrollContent,
                {
                  paddingHorizontal: metrics.screenGutter,
                  paddingTop: spacing.xxxl + spacing.md,
                  paddingBottom: spacing.xxl,
                },
              ]}
              keyboardDismissMode={Platform.OS === 'ios' ? 'interactive' : 'on-drag'}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >

              {!isKeyboardVisible && (
                <Animated.View
                  className="gap-3"
                  entering={animationsReady ? FadeInDown.duration(motion.duration.standard).easing(Easing.out(Easing.quad)) : undefined}
                  exiting={FadeOutUp.duration(motion.duration.standard).easing(Easing.out(Easing.quad))}
                  style={styles.headingGroup}
                >
                  <Text
                    accessibilityRole="header"
                    ref={titleRef}
                    style={[
                      typography.authTitle,
                      styles.title,
                      previewTextScale !== 1
                        ? {
                          fontSize: typography.authTitle.fontSize * previewTextScale,
                          lineHeight: typography.authTitle.lineHeight * previewTextScale,
                        }
                        : null,
                    ]}
                  >
                    {title}
                  </Text>
                  <Text
                    style={[
                      typography.body,
                      styles.supportingText,
                      previewTextScale !== 1
                        ? {
                          fontSize: typography.body.fontSize * previewTextScale,
                          lineHeight: typography.body.lineHeight * previewTextScale,
                        }
                        : null,
                    ]}
                  >
                    {supportingText}
                  </Text>
                </Animated.View>
              )}

              <Animated.View className="gap-6" layout={animationsReady ? LinearTransition.duration(motion.duration.standard).easing(Easing.out(Easing.quad)) : undefined} style={styles.content}>
                {children}
              </Animated.View>

              {actions ? <Animated.View className="gap-3" layout={animationsReady ? LinearTransition.duration(motion.duration.standard).easing(Easing.out(Easing.quad)) : undefined}>{actions}</Animated.View> : null}
            </ScrollView>
          </KeyboardAvoidingView>
        </SafeAreaView>
      </View>
    </AuthLayoutContext.Provider>
  );
}

const styles = StyleSheet.create({
  canvas: {
    backgroundColor: authPresentationColors.canvas,
  },
  scrollContent: {
    flexGrow: 1,
    width: '100%',
    maxWidth: contentMaxWidths.form,
    alignSelf: 'center',
  },
  backButton: {
    minWidth: sizes.touchTarget.minimumWidth,
    minHeight: sizes.touchTarget.minimumHeight,
  },
  headingGroup: {
    marginTop: spacing.xl,
    marginBottom: spacing.xl,
  },
  title: {
    color: darkColors.textPrimary,
  },
  supportingText: {
    color: darkColors.textSecondary,
  },
  content: {
    flexGrow: 1,
  },
});
