import React, { useState, useEffect } from 'react';
import { View, Pressable, Text, StyleSheet, Animated, useColorScheme } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Ionicons, Feather, Entypo } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import * as NavigationBar from 'expo-navigation-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { PhosphorHouse } from '@/components/icons/PhosphorHouse';
import { BlurView } from 'expo-blur';

export function EliteGlassTabBar() {
  const { t } = useTranslation();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState('home');

  const paddingBottom = Math.max(insets.bottom, 16);

  return (
    <View className="absolute bottom-0 left-0 right-0">
      <NavigationBar.NavigationBar style={isDark ? 'light' : 'dark'} />
      {/* 
        Spotify style feathered blur: 
        1. A BlurView for the glass effect 
        2. A LinearGradient mask that fades from transparent to solid background color
      */}
      <BlurView intensity={isDark ? 50 : 80} tint={isDark ? 'dark' : 'light'} style={StyleSheet.absoluteFill} />
      <LinearGradient 
        colors={[
          'transparent', 
          isDark ? 'rgba(9,9,11,1)' : 'rgba(255,255,255,1)',
          isDark ? 'rgba(9,9,11,1)' : 'rgba(255,255,255,1)'
        ]} 
        locations={[0, 0.35, 1]}
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
