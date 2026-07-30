import { Tabs } from 'expo-router';
import { useTheme } from '@/hooks/use-theme';
import { EliteTabBar } from '@/components/navigation/EliteTabBar';

export default function TabsLayout() {
  const theme = useTheme();

  return (
    <Tabs
      tabBar={(props) => <EliteTabBar {...(props as any)} />}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: theme.colors.screen }, // Prevents white flashes during navigation
      }}
    >
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="expenses" options={{ title: 'Expenses' }} />
      <Tabs.Screen name="add" options={{ title: 'Add' }} />
      <Tabs.Screen name="budgets" options={{ title: 'Budgets' }} />
      <Tabs.Screen name="more" options={{ title: 'More' }} />
    </Tabs>
  );
}
