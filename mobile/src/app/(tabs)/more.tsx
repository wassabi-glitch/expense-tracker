import React from 'react';
import { StyleSheet, Text, View, ScrollView, Pressable, useColorScheme } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme, useThemePreference } from '@/hooks/use-theme';
import { useTranslation } from 'react-i18next';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

type ListItemProps = {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  href?: string;
  isLast?: boolean;
  value?: string;
  onPress?: () => void;
};

export default function MoreScreen() {
  const theme = useTheme();
  const { t } = useTranslation();
  const { preference, setPreference } = useThemePreference();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const insets = useSafeAreaInsets();
  const router = useRouter();

  const handleThemeCycle = () => {
    const next = preference === 'system' ? 'dark' : preference === 'dark' ? 'light' : 'system';
    setPreference(next);
  };

  const themeDisplayNames = {
    system: 'System',
    light: 'Light',
    dark: 'Dark'
  };

  const ListItem = ({ icon, label, href, isLast = false, value, onPress }: ListItemProps) => {
    return (
      <Pressable 
        className="flex-row items-center px-4 py-4"
        style={({ pressed }) => [
          { backgroundColor: pressed ? theme.colors.surfaceSubtle : 'transparent' }
        ]}
        onPress={() => onPress ? onPress() : href ? router.push(href as any) : null}
      >
        <Ionicons name={icon} size={22} color={theme.colors.brand.action} style={{ marginRight: 16 }} />
        <Text style={[theme.typography.body, { color: theme.colors.textPrimary, flex: 1, fontWeight: '500' }]}>
          {label}
        </Text>
        {value ? (
          <Text style={[theme.typography.body, { color: theme.colors.textSecondary, marginRight: 8 }]}>
            {value}
          </Text>
        ) : null}
        <Ionicons name="chevron-forward" size={20} color={theme.colors.borderControl} />
      </Pressable>
    );
  };

  const ListGroup = ({ title, children }: { title: string, children: React.ReactNode }) => {
    return (
      <View className="mb-6">
        <Text style={[theme.typography.supporting, { color: theme.colors.textSecondary, marginLeft: 16, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1, fontWeight: '600' }]}>
          {title}
        </Text>
        <View 
          className="rounded-2xl overflow-hidden" 
          style={{ 
            backgroundColor: theme.colors.surface
          }}
        >
          {children}
        </View>
      </View>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.screen }]}>
      <View 
        className="absolute top-0 left-0 right-0 justify-end px-4 z-10"
        style={{ 
          backgroundColor: theme.colors.screen,
          paddingTop: insets.top + 12, 
          paddingBottom: 12, 
        }}
      >
        <Text style={[theme.typography.title, { color: theme.colors.textPrimary }]}>
          {t('layout.tabs.more')}
        </Text>
      </View>
      <ScrollView 
        contentContainerStyle={{ 
          paddingTop: insets.top + 60, 
          paddingBottom: insets.bottom + 120,
          paddingHorizontal: 16
        }}
      >
        <ListGroup title={t('moreScreen.groups.finances')}>
          <ListItem icon="wallet-outline" label={t('moreScreen.items.wallets')} href="/wallets" />
          <ListItem icon="flag-outline" label={t('moreScreen.items.goals')} href="/goals" />
          <ListItem icon="document-text-outline" label={t('moreScreen.items.obligations')} href="/obligations" />
          <ListItem icon="cash-outline" label={t('moreScreen.items.income')} href="/income" />
          <ListItem icon="briefcase-outline" label={t('moreScreen.items.assets')} href="/assets" isLast />
        </ListGroup>

        <ListGroup title={t('moreScreen.groups.insights')}>
          <ListItem icon="pie-chart-outline" label={t('moreScreen.items.analytics')} href="/analytics" />
          <ListItem icon="download-outline" label={t('moreScreen.items.export')} href="/export" isLast />
        </ListGroup>

        <ListGroup title={t('moreScreen.groups.general')}>
          <ListItem 
            icon="moon-outline" 
            label={t('moreScreen.items.appearance')} 
            value={themeDisplayNames[preference]} 
            onPress={handleThemeCycle} 
          />
          <ListItem icon="settings-outline" label={t('moreScreen.items.settings')} href="/settings" isLast />
        </ListGroup>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  title: {
    textAlign: 'left',
  }
});
