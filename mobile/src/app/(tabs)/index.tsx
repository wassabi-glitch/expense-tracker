import { StyleSheet, Text, View } from 'react-native';
import { Link } from 'expo-router';

import { useTheme } from '@/hooks/use-theme';

export default function HomeScreen() {
  const theme = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.screen }]}>
      <Text
        style={[
          styles.title,
          theme.typography.title,
          { color: theme.colors.textPrimary },
        ]}
      >
        Sarflog mobile is running 🎉
      </Text>

      <Link href="/auth-preview" style={[styles.link, { color: theme.colors.brand.action }]}>
        Open Auth Preview
      </Link>

      <Link href="/layout-preview" style={[styles.link, { color: theme.colors.brand.action }]}>
        Open Layout Preview
      </Link>

      <Link href="/(auth)/sign-up" style={[styles.link, { color: theme.colors.brand.action }]}>
        Open Real Auth Flow
      </Link>
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
    marginBottom: 20,
  },
  link: {
    fontSize: 18,
    fontWeight: 'bold',
    padding: 10,
  },
});
