import React, { useState } from 'react';
import { View, Pressable, Text, StyleSheet, Animated, useColorScheme } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Ionicons, Feather } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import { LinearGradient } from 'expo-linear-gradient';
import { PhosphorHouse } from '@/components/icons/PhosphorHouse';
import { BlurView } from 'expo-blur';

export function PremiumGlassTabBar() {
  const { t } = useTranslation();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState('home');

  const paddingBottom = Math.max(insets.bottom, 16);

  return (
    <View className="absolute bottom-0 left-0 right-0">

      {/* 1. Variable Blur Layers - Progressive Glass Foundation */}
      <View style={StyleSheet.absoluteFill}>
        {/* Layer 1: Very top edge starts at 15 intensity */}
        <BlurView 
          intensity={isDark ? 15 : 25} 
          tint={isDark ? 'dark' : 'light'} 
          style={StyleSheet.absoluteFill} 
        />
        {/* Layer 2: Middle section jumps to 45 intensity (starts 12px down) */}
        <BlurView 
          intensity={isDark ? 45 : 60} 
          tint={isDark ? 'dark' : 'light'} 
          style={[StyleSheet.absoluteFill, { top: 12 }]} 
        />
        {/* Layer 3: Main body is maximum 85 intensity (starts 28px down) */}
        <BlurView 
          intensity={isDark ? 85 : 100} 
          tint={isDark ? 'dark' : 'light'} 
          style={[StyleSheet.absoluteFill, { top: 28 }]} 
        />
      </View>

      {/* 2. Nuanced Multi-Stage Gradient Overlay */}
      <LinearGradient
        colors={[
          // TOP: The "brightest glass" part. Highly transparent, bright highlight to seamlessly merge into the content above.
          isDark ? 'rgba(9,9,9,0.01)' : 'rgba(255,255,255,0.7)',

          // MIDDLE-TOP: Start fading into the true glass color
          isDark ? 'rgba(9,9,11,0.2)' : 'rgba(255,255,255,0.9)',

          // MIDDLE-BOTTOM: The darker glass body behind the icons
          isDark ? 'rgba(9,9,11,0.75)' : 'rgba(240,240,240,0.95)',

          // BOTTOM: Solid dark for the Android Navigation territory
          isDark ? 'rgba(9,9,11,1)' : 'rgba(255,255,255,1)'
        ]}
        locations={[0, 0.25, 0.6, 1]}
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

        <TabButton
          icon={<Ionicons name="add-circle-outline" size={28} color={theme.colors.textSecondary} />}
          activeIcon={<Ionicons name="add-circle" size={28} color={theme.colors.brand.action} />}
          label="Add"
          isActive={activeTab === 'add'}
          onPress={() => setActiveTab('add')}
        />

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
