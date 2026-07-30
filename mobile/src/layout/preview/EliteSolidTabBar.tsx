import React, { useState, useEffect } from 'react';
import { View, Pressable, Text, Animated, useColorScheme } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Ionicons, Feather, Entypo } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import * as NavigationBar from 'expo-navigation-bar';
import { PhosphorHouse } from '@/components/icons/PhosphorHouse';

export function EliteSolidTabBar() {
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState('home');
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';

  const paddingBottom = Math.max(insets.bottom, 16);

  return (
    <View 
      style={{ paddingBottom }}
      className="flex-row items-center justify-between bg-white dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 px-2 pt-2"
    >
      <NavigationBar.NavigationBar style={isDark ? 'light' : 'dark'} />
      <TabButton 
        icon={<PhosphorHouse size={24} color={theme.colors.textSecondary} weight="regular" />}
        activeIcon={<PhosphorHouse size={24} color={theme.colors.brand.action} weight="fill" />}
        label={t('layout.tabs.home')}
        isActive={activeTab === 'home'}
        onPress={() => setActiveTab('home')}
      />
      <TabButton 
        icon={<Ionicons name="receipt-outline" size={24} color={theme.colors.textSecondary} />}
        activeIcon={<Ionicons name="receipt" size={24} color={theme.colors.brand.action} />}
        label={t('layout.tabs.expenses')}
        isActive={activeTab === 'expenses'}
        onPress={() => setActiveTab('expenses')}
      />
      
      {/* Center Action Button */}
      <View className="relative -top-5 justify-center items-center">
        <Pressable className="bg-green-600 active:bg-green-700 h-14 w-14 rounded-full items-center justify-center shadow-lg shadow-green-600/30">
          <Ionicons name="add" size={32} color="white" />
        </Pressable>
      </View>

      <TabButton 
        icon={<Ionicons name="pie-chart-outline" size={24} color={theme.colors.textSecondary} />}
        activeIcon={<Ionicons name="pie-chart" size={24} color={theme.colors.brand.action} />}
        label={t('layout.tabs.budgets')}
        isActive={activeTab === 'budgets'}
        onPress={() => setActiveTab('budgets')}
      />
      <TabButton 
        icon={<Feather name="menu" size={24} color={theme.colors.textSecondary} />}
        activeIcon={<Feather name="menu" size={24} color={theme.colors.brand.action} />}
        label={t('layout.tabs.more')}
        isActive={activeTab === 'more'}
        onPress={() => setActiveTab('more')}
      />
    </View>
  );
}

function TabButton({ icon, activeIcon, label, isActive, onPress }: { icon: React.ReactNode, activeIcon: React.ReactNode, label: string, isActive: boolean, onPress: () => void }) {
  const [scale] = useState(new Animated.Value(1));

  const handlePressIn = () => {
    Animated.spring(scale, {
      toValue: 0.85,
      useNativeDriver: true,
    }).start();
  };

  const handlePressOut = () => {
    Animated.spring(scale, {
      toValue: 1,
      useNativeDriver: true,
    }).start();
    onPress();
  };

  return (
    <Pressable 
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      className="flex-1 items-center justify-center h-12"
      hitSlop={8}
    >
      <Animated.View style={{ transform: [{ scale }] }} className="items-center justify-center">
        <View className="mb-1">
          {isActive ? activeIcon : icon}
        </View>
        <Text className={`text-[10px] font-medium ${isActive ? 'text-green-600 dark:text-green-500' : 'text-zinc-500'}`}>
          {label}
        </Text>
      </Animated.View>
    </Pressable>
  );
}
