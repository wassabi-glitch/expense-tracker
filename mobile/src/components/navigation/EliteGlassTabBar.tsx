import React, { useState } from 'react';
import { View, Pressable, Text, StyleSheet, Animated, useColorScheme } from 'react-native';
import { useTranslation } from 'react-i18next';
import { Ionicons, Feather, Entypo } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '@/hooks/use-theme';
import * as NavigationBar from 'expo-navigation-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { PhosphorHouse } from '@/components/icons/PhosphorHouse';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { BlurView } from 'expo-blur';

export function EliteGlassTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const { t } = useTranslation();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const insets = useSafeAreaInsets();
  const theme = useTheme();

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
          isDark ? 'rgba(9,9,11,0.75)' : 'rgba(255,255,255,0.85)',
          isDark ? 'rgba(9,9,11,1)' : 'rgba(255,255,255,1)'
        ]}
        locations={[0, 0.4, 0.9]}
        style={StyleSheet.absoluteFill}
      />

      <View style={{ paddingBottom }} className="flex-row items-center justify-between px-2 pt-2">
        {state.routes.map((route, index) => {
          const { options } = descriptors[route.key];
          const label = options.tabBarLabel !== undefined
            ? options.tabBarLabel
            : options.title !== undefined
            ? options.title
            : route.name;

          const isFocused = state.index === index;

          const onPress = () => {
            const event = navigation.emit({
              type: 'tabPress',
              target: route.key,
              canPreventDefault: true,
            });

            if (!isFocused && !event.defaultPrevented) {
              navigation.navigate(route.name, route.params);
            }
          };

          let icon;
          let activeIcon;
          let displayLabel = typeof label === 'string' ? label : route.name;

          if (route.name === 'index') {
            icon = <PhosphorHouse size={24} color={theme.colors.textSecondary} weight="regular" />;
            activeIcon = <PhosphorHouse size={24} color={theme.colors.brand.action} weight="fill" />;
            displayLabel = t('layout.tabs.home');
          } else if (route.name === 'expenses') {
            icon = <Ionicons name="receipt-outline" size={24} color={theme.colors.textSecondary} />;
            activeIcon = <Ionicons name="receipt" size={24} color={theme.colors.brand.action} />;
            displayLabel = t('layout.tabs.expenses');
          } else if (route.name === 'add') {
            icon = <Ionicons name="add-circle-outline" size={28} color={theme.colors.textSecondary} />;
            activeIcon = <Ionicons name="add-circle" size={28} color={theme.colors.brand.action} />;
            displayLabel = t('layout.tabs.add');
          } else if (route.name === 'budgets') {
            icon = <Ionicons name="pie-chart-outline" size={24} color={theme.colors.textSecondary} />;
            activeIcon = <Ionicons name="pie-chart" size={24} color={theme.colors.brand.action} />;
            displayLabel = t('layout.tabs.budgets');
          } else if (route.name === 'more') {
            icon = <Feather name="menu" size={24} color={theme.colors.textSecondary} />;
            activeIcon = <Feather name="menu" size={24} color={theme.colors.brand.action} />;
            displayLabel = t('layout.tabs.more');
          } else {
            // Fallback for unknown routes
            icon = <Feather name="circle" size={24} color={theme.colors.textSecondary} />;
            activeIcon = <Feather name="circle" size={24} color={theme.colors.brand.action} />;
          }

          return (
            <TabButton
              key={route.key}
              icon={icon}
              activeIcon={activeIcon}
              label={displayLabel}
              isActive={isFocused}
              onPress={onPress}
            />
          );
        })}
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
