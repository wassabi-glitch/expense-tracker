import React, { useState } from 'react';
import { View, Pressable, Text, StyleSheet, Animated, useColorScheme } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Ionicons, Feather } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import { LinearGradient } from 'expo-linear-gradient';
import { PhosphorHouse } from '@/components/icons/PhosphorHouse';
import { BlurView } from 'expo-blur';

export function EliteMiniFabTabBar() {
  const { t } = useTranslation();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState('home');

  const paddingBottom = Math.max(insets.bottom, 16);

  return (
    <View className="absolute bottom-0 left-0 right-0">
      
      {/* 1. Base Blur Layer */}
      <BlurView 
        intensity={isDark ? 50 : 80} 
        tint={isDark ? 'dark' : 'light'} 
        style={StyleSheet.absoluteFill} 
      />

      {/* 2. Gradient mask that darkens the middle section for text readability */}
      <LinearGradient
        colors={[
          'transparent',
          isDark ? 'rgba(9,9,11,0.75)' : 'rgba(255,255,255,0.85)',
          isDark ? 'rgba(9,9,11,1)' : 'rgba(255,255,255,1)'
        ]}
        locations={[0, 0.4, 0.9]}
        style={StyleSheet.absoluteFill}
      />

      <View style={{ paddingBottom }} className="flex-row items-center justify-between px-2 pt-4">
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

        {/* --- THE MINI FAB --- */}
        <View className="flex-1 items-center justify-center h-12">
          <Pressable
            onPress={() => setActiveTab('add')}
            className={`w-[46px] h-[46px] rounded-2xl items-center justify-center active:scale-95 transition-transform shadow-sm ${isDark ? 'bg-green-500' : 'bg-green-600'}`}
            style={{ 
              shadowColor: isDark ? '#22c55e' : '#16a34a', 
              shadowOpacity: isDark ? 0.4 : 0.3, 
              shadowRadius: 8, 
              shadowOffset: { width: 0, height: 4 },
              elevation: 4 
            }}
          >
            <Ionicons name="add" size={28} color="white" />
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
