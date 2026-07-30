import { StyleSheet, Text, View } from 'react-native';
import { useTheme } from '@/hooks/use-theme';

export default function BudgetsScreen() {
  const theme = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.screen }]}>
      <Text style={[styles.title, theme.typography.title, { color: theme.colors.textPrimary }]}>
        Budgets
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    textAlign: 'center',
  },
});
