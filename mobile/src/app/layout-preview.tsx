import React, { useState } from 'react';
import { View, Text, ScrollView, Pressable, useColorScheme } from 'react-native';
import { Redirect } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useThemePreference } from '@/hooks/use-theme';
import { SolidTabBar } from '@/layout/preview/SolidTabBar';
import { GlassTabBar } from '@/layout/preview/GlassTabBar';
import { EliteSolidTabBar } from '@/layout/preview/EliteSolidTabBar';
import { EliteGlassTabBar } from '@/layout/preview/EliteGlassTabBar';
import { PremiumGlassTabBar } from '@/layout/preview/PremiumGlassTabBar';
import { EliteMiniFabTabBar } from '@/layout/preview/EliteMiniFabTabBar';
import { PlaygroundGlassTabBar } from '@/layout/preview/PlaygroundGlassTabBar';

export default function LayoutPreviewRoute() {
  // Guard the preview route
  if (!__DEV__) {
    return <Redirect href="/" />;
  }

  const { t } = useTranslation();
  const [tabType, setTabType] = useState<'solid' | 'glass' | 'elite-solid' | 'elite-glass' | 'elite-solid-std' | 'elite-glass-std' | 'elite-mini-fab' | 'premium-glass' | 'playground'>('playground');
  const { preference, setPreference } = useThemePreference();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';

  // Playground State
  const [opacity, setOpacity] = useState(0.85);
  const [blur, setBlur] = useState(isDark ? 50 : 80);

  const adjustValue = (setter: React.Dispatch<React.SetStateAction<number>>, delta: number, min: number, max: number) => {
    setter(prev => Math.min(max, Math.max(min, Number((prev + delta).toFixed(2)))));
  };

  // Generate some dummy content to test scrolling under the glass tab bar
  const dummyItems = Array.from({ length: 20 }, (_, i) => i + 1);

  return (
    <View className="flex-1 bg-zinc-50 dark:bg-zinc-900">
      {/* Mock Header */}
      <View className="pt-14 pb-4 px-4 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800">
        <Text className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Layout Gallery
        </Text>
      </View>

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ paddingBottom: 120 }} // Extra padding so content isn't trapped under absolute glass bar
      >
        <View className="p-4 space-y-6">
          <View>
            <Text className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-3">
              {t('layout.preview.galleryLabel')}
            </Text>
            <View className="space-y-2">
              <ToggleOption
                label={t('layout.preview.solidTab')}
                isSelected={tabType === 'solid'}
                onSelect={() => setTabType('solid')}
              />
              <ToggleOption
                label={t('layout.preview.glassTab')}
                isSelected={tabType === 'glass'}
                onSelect={() => setTabType('glass')}
              />
              <ToggleOption
                label="Elite Solid Tab (Ionicons)"
                isSelected={tabType === 'elite-solid'}
                onSelect={() => setTabType('elite-solid')}
              />
              <ToggleOption
                label="Elite Glass Tab (Spotify Gradient)"
                isSelected={tabType === 'elite-glass'}
                onSelect={() => setTabType('elite-glass')}
              />
              <ToggleOption
                label="Premium Feathered Glass (Nuanced)"
                isSelected={tabType === 'premium-glass'}
                onSelect={() => setTabType('premium-glass')}
              />
              <ToggleOption
                label="Signature Elite Mini-FAB (Glass)"
                isSelected={tabType === 'elite-mini-fab'}
                onSelect={() => setTabType('elite-mini-fab')}
              />
              <ToggleOption
                label="🧪 RGBA Glass Playground"
                isSelected={tabType === 'playground'}
                onSelect={() => setTabType('playground')}
              />
            </View>
          </View>

          {/* Render Playground Controls if Playground is selected */}
          {tabType === 'playground' && (
            <View className="mb-6 p-4 bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 shadow-sm">
              <Text className="text-zinc-900 dark:text-white font-bold mb-4 text-center">RGBA Glass Playground</Text>
              
              <ControlRow 
                label={`Tint Opacity: ${opacity.toFixed(2)}`} 
                onMinus={() => adjustValue(setOpacity, -0.05, 0, 1)}
                onPlus={() => adjustValue(setOpacity, 0.05, 0, 1)}
              />
              <ControlRow 
                label={`Blur Intensity: ${blur}`} 
                onMinus={() => adjustValue(setBlur, -5, 0, 100)}
                onPlus={() => adjustValue(setBlur, 5, 0, 100)}
              />
            </View>
          )}

          <View>
            <Text className="text-sm font-medium text-zinc-500 uppercase tracking-wider mb-3">
              Theme Controls
            </Text>
            <View className="flex-row space-x-2">
              <View className="flex-1">
                <ToggleOption
                  label="Light"
                  isSelected={preference === 'light'}
                  onSelect={() => setPreference('light')}
                />
              </View>
              <View className="flex-1">
                <ToggleOption
                  label="Dark"
                  isSelected={preference === 'dark'}
                  onSelect={() => setPreference('dark')}
                />
              </View>
            </View>
          </View>

          <View className="mt-8 space-y-4">
            <Text className="text-lg font-medium text-zinc-900 dark:text-zinc-100">
              Mock Content Area
            </Text>
            <Text className="text-base text-zinc-600 dark:text-zinc-400">
              Scroll down to see how the content interacts with the tab bar (especially the Glass bar).
            </Text>

            {dummyItems.map(item => (
              <View key={item} className="bg-white dark:bg-zinc-800 p-4 rounded-xl border border-zinc-200 dark:border-zinc-700">
                <Text className="text-zinc-900 dark:text-zinc-100 font-medium">Mock Feed Item {item}</Text>
                <Text className="text-zinc-500 dark:text-zinc-400 mt-1">This is a fake transaction to test scrolling.</Text>
              </View>
            ))}
          </View>
        </View>
      </ScrollView>

      {/* Render the selected Tab Bar */}
      {tabType === 'solid' && <SolidTabBar />}
      {tabType === 'glass' && <GlassTabBar />}
      {tabType === 'elite-solid' && <EliteSolidTabBar />}
      {tabType === 'elite-glass' && <EliteGlassTabBar />}
      {tabType === 'elite-mini-fab' && <EliteMiniFabTabBar />}
      {tabType === 'premium-glass' && <PremiumGlassTabBar />}
      {tabType === 'playground' && <PlaygroundGlassTabBar opacity={opacity} blur={blur} />}
    </View>
  );
}

function ControlRow({ label, onMinus, onPlus }: { label: string, onMinus: () => void, onPlus: () => void }) {
  return (
    <View className="flex-row items-center justify-between mb-3">
      <Text className="text-zinc-700 dark:text-zinc-300 flex-1">{label}</Text>
      <View className="flex-row items-center space-x-2">
        <Pressable onPress={onMinus} className="bg-zinc-200 dark:bg-zinc-800 w-10 h-10 rounded-full items-center justify-center">
          <Text className="text-zinc-900 dark:text-white text-lg font-bold">-</Text>
        </Pressable>
        <Pressable onPress={onPlus} className="bg-zinc-200 dark:bg-zinc-800 w-10 h-10 rounded-full items-center justify-center">
          <Text className="text-zinc-900 dark:text-white text-lg font-bold">+</Text>
        </Pressable>
      </View>
    </View>
  );
}

function ToggleOption({ label, isSelected, onSelect }: { label: string, isSelected: boolean, onSelect: () => void }) {
  return (
    <Pressable
      onPress={onSelect}
      className={`p-4 rounded-xl border flex-row items-center justify-between ${isSelected
          ? 'bg-green-50 dark:bg-green-950/30 border-green-500 dark:border-green-600'
          : 'bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700'
        }`}
    >
      <Text className={`font-medium ${isSelected ? 'text-green-700 dark:text-green-400' : 'text-zinc-900 dark:text-zinc-100'}`}>
        {label}
      </Text>
      {isSelected && (
        <View className="w-4 h-4 rounded-full bg-green-500" />
      )}
    </Pressable>
  );
}
