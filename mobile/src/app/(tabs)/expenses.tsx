import { StyleSheet, Text, View, ScrollView } from 'react-native';
import { useTheme } from '@/hooks/use-theme';

export default function ExpensesScreen() {
  const theme = useTheme();
  
  // Generate 30 fake transactions
  const fakeTransactions = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    title: `Groceries ${i + 1}`,
    amount: `-$${(Math.random() * 100).toFixed(2)}`,
    date: `2026-07-${(i % 30) + 1}`,
  }));

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.screen }]}>
      <View style={styles.header}>
        <Text style={[styles.title, theme.typography.title, { color: theme.colors.textPrimary }]}>
          Expenses
        </Text>
      </View>
      
      {/* ScrollView with contentContainerStyle paddingBottom so content isn't trapped under the tab bar */}
      <ScrollView contentContainerStyle={{ paddingBottom: 120, paddingHorizontal: 16 }}>
        {fakeTransactions.map((tx) => (
          <View 
            key={tx.id} 
            style={[styles.transactionCard, { backgroundColor: theme.colors.surface, borderColor: theme.colors.borderSubtle }]}
          >
            <View>
              <Text style={[theme.typography.body, { color: theme.colors.textPrimary, fontWeight: 'bold' }]}>
                {tx.title}
              </Text>
              <Text style={[theme.typography.supporting, { color: theme.colors.textSecondary }]}>
                {tx.date}
              </Text>
            </View>
            <Text style={[theme.typography.body, { color: theme.colors.textPrimary }]}>
              {tx.amount}
            </Text>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 60, // give some room at the top
  },
  header: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  title: {
    textAlign: 'left',
  },
  transactionCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    marginBottom: 12,
    borderRadius: 12,
    borderWidth: 1,
  }
});
