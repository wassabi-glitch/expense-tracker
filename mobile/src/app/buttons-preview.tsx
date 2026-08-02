import React from 'react';
import { View, ScrollView, Text, useColorScheme } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import { AppButton } from '@/components/ui/app-button';
import { Ionicons } from '@expo/vector-icons';

export default function ButtonsPreviewScreen() {
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';

  const Section = ({ title, children }: { title: string, children: React.ReactNode }) => (
    <View className="mb-8">
      <Text style={[theme.typography.supporting, { color: theme.colors.textSecondary, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1, fontWeight: '600' }]}>
        {title}
      </Text>
      <View className="gap-4">
        {children}
      </View>
    </View>
  );

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.screen }}>
      <View
        style={{
          paddingTop: insets.top + 16,
          paddingHorizontal: 20,
          paddingBottom: 16,
          borderBottomWidth: 1,
          borderBottomColor: theme.colors.borderSubtle,
        }}
      >
        <Text style={[theme.typography.title, { color: theme.colors.textPrimary }]}>
          Buttons Gallery
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 20, paddingBottom: insets.bottom + 40 }}>
        
        <Section title="Sizes">
          <View className="flex-row items-center space-x-4 mb-4">
            <AppButton size="sm">Small</AppButton>
            <AppButton size="md">Medium</AppButton>
            <AppButton size="lg">Large</AppButton>
          </View>
          <View className="flex-row items-center space-x-4">
            <AppButton size="lg" isLoading>Large Loading</AppButton>
          </View>
        </Section>

        <Section title="Primary">
          <AppButton variant="primary">
            Primary Default
          </AppButton>
          <AppButton variant="primary" isDisabled>
            Primary Disabled
          </AppButton>
          <AppButton variant="primary" isLoading>
            Primary Loading
          </AppButton>
          <View className="h-2" />
          <AppButton variant="primary">
            <Ionicons name="add" size={20} color={isDark ? '#000' : '#fff'} style={{ marginRight: 8 }} />
            <AppButton.Label>With Icon</AppButton.Label>
          </AppButton>
        </Section>

        <Section title="Secondary">
          <AppButton variant="secondary">
            Secondary Default
          </AppButton>
          <AppButton variant="secondary" isDisabled>
            Secondary Disabled
          </AppButton>
          <AppButton variant="secondary" isLoading>
            Secondary Loading
          </AppButton>
        </Section>

        <Section title="Tertiary & Ghost">
          <AppButton variant="tertiary">
            Tertiary Action
          </AppButton>
          <AppButton variant="tertiary" isDisabled>
            Tertiary Disabled
          </AppButton>
          <AppButton variant="tertiary" isLoading>
            Tertiary Loading
          </AppButton>
          
          <View className="h-4" />
          
          <AppButton variant="ghost">
            Ghost Action
          </AppButton>
          <AppButton variant="ghost" isDisabled>
            Ghost Disabled
          </AppButton>
          <AppButton variant="ghost" isLoading>
            Ghost Loading
          </AppButton>
          
          <View className="h-4" />
          <AppButton variant="outline">
            Outline Action
          </AppButton>
          <AppButton variant="outline" isDisabled>
            Outline Disabled
          </AppButton>
          <AppButton variant="outline" isLoading>
            Outline Loading
          </AppButton>
        </Section>

        <Section title="Danger">
          <AppButton variant="danger">
            Danger Action
          </AppButton>
          <AppButton variant="danger" isDisabled>
            Danger Disabled
          </AppButton>
          <AppButton variant="danger" isLoading>
            Danger Loading
          </AppButton>

          <View className="h-4" />

          <AppButton variant="danger-soft">
            Danger Soft Action
          </AppButton>
          <AppButton variant="danger-soft" isDisabled>
            Danger Soft Disabled
          </AppButton>
          <AppButton variant="danger-soft" isLoading>
            Danger Soft Loading
          </AppButton>
        </Section>

      </ScrollView>
    </View>
  );
}
