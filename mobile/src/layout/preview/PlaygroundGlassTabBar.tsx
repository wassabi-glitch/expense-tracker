import React, { useState } from 'react';
import { View, Pressable, Text, StyleSheet, Animated, useColorScheme } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Ionicons, Feather, Entypo } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import * as NavigationBar from 'expo-navigation-bar';
import { PhosphorHouse } from '@/components/icons/PhosphorHouse';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';

export function PlaygroundGlassTabBar({ opacity = 0.85, blur = 80, rgbColor = '0,0,0' }: { opacity?: number, blur?: number, rgbColor?: string }) {
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

      <BlurView intensity={blur} tint={isDark ? 'dark' : 'light'} style={StyleSheet.absoluteFill} />
      <LinearGradient
        colors={[
          'transparent',
          isDark ? `rgba(${rgbColor},${opacity})` : `rgba(255,255,255,${opacity})`,
          isDark ? `rgba(${rgbColor},1)` : 'rgba(255,255,255,1)'
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
        <View className="flex-1 items-center justify-center -mt-6">
          <Pressable 
            className="w-14 h-14 bg-green-500 rounded-full items-center justify-center shadow-md shadow-green-500/30"
          >
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
