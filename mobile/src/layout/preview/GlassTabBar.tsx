import React, { useState } from 'react';
import { View, Pressable, Text, StyleSheet, Animated } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Home, Receipt, PiggyBank, Menu, Plus } from 'lucide-react-native';
import { useColorScheme } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';

export function GlassTabBar() {
  const { t } = useTranslation();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState('home');

  const paddingBottom = Math.max(insets.bottom, 16);

  return (
    <View className="absolute bottom-0 left-0 right-0">
      <View 
        style={[StyleSheet.absoluteFill, { backgroundColor: isDark ? 'rgba(0,0,0,0.7)' : 'rgba(255,255,255,0.8)' }]}
        className="border-t border-zinc-200 dark:border-zinc-800"
      />
      <View style={{ paddingBottom }} className="flex-row items-center justify-between px-2 pt-2">
        <TabButton 
          icon={<Home size={24} color={theme.colors.textSecondary} />}
          activeIcon={<Home size={24} color={theme.colors.brand.action} fill={theme.colors.brand.action} />}
          label={t('layout.tabs.home')}
          isActive={activeTab === 'home'}
          onPress={() => setActiveTab('home')}
        />
        <TabButton 
          icon={<Receipt size={24} color={theme.colors.textSecondary} />}
          activeIcon={<Receipt size={24} color={theme.colors.brand.action} fill={theme.colors.brand.action} />}
          label={t('layout.tabs.expenses')}
          isActive={activeTab === 'expenses'}
          onPress={() => setActiveTab('expenses')}
        />
        
        {/* Center Action Button */}
        <View className="relative -top-5 justify-center items-center">
          <Pressable className="bg-green-600 active:bg-green-700 h-14 w-14 rounded-full items-center justify-center shadow-lg shadow-green-600/30">
            <Plus size={32} color="white" />
          </Pressable>
        </View>

        <TabButton 
          icon={<PiggyBank size={24} color={theme.colors.textSecondary} />}
          activeIcon={<PiggyBank size={24} color={theme.colors.brand.action} fill={theme.colors.brand.action} />}
          label={t('layout.tabs.budgets')}
          isActive={activeTab === 'budgets'}
          onPress={() => setActiveTab('budgets')}
        />
        <TabButton 
          icon={<Menu size={24} color={theme.colors.textSecondary} />}
          activeIcon={<Menu size={24} color={theme.colors.brand.action} fill={theme.colors.brand.action} />}
          label={t('layout.tabs.more')}
          isActive={activeTab === 'more'}
          onPress={() => setActiveTab('more')}
        />
      </View>
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
