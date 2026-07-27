import type { PropsWithChildren } from 'react';
import { Button } from '@/components/ui/button';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BottomTabInset, MaxContentWidth } from '@/constants/layout';
import { useTheme, useThemePreference } from '@/hooks/use-theme';
import {
  useAdaptiveLayout,
  type WindowHeightClass,
  type WindowWidthClass,
} from '@/layout';
import {
  fontFamilies,
  radii,
  sizes,
  spacing,
  type StatusColors,
  type ThemePreference,
} from '@/theme';

const appearanceOptions = [
  ['system', 'System'],
  ['light', 'Light'],
  ['dark', 'Dark'],
] as const satisfies readonly (readonly [ThemePreference, string])[];

const noop = () => undefined;
const useHeroWebFallback = Platform.OS === 'web';

const widthClassLabels = {
  compact: 'Compact',
  medium: 'Medium',
  expanded: 'Expanded',
} as const satisfies Record<WindowWidthClass, string>;

const heightClassLabels = {
  compact: 'Compact',
  regular: 'Regular',
} as const satisfies Record<WindowHeightClass, string>;

const spacingSamples = [
  ['XXS', spacing.xxs],
  ['XS', spacing.xs],
  ['SM', spacing.sm],
  ['MD', spacing.md],
  ['LG', spacing.lg],
  ['XL', spacing.xl],
  ['XXL', spacing.xxl],
  ['XXXL', spacing.xxxl],
] as const;

const radiusSamples = [
  ['Small', radii.small],
  ['Medium', radii.medium],
  ['Large', radii.large],
  ['Extra large', radii.extraLarge],
  ['Full', radii.full],
] as const;

const controlSamples = [
  ['Compact', sizes.controlHeight.compact],
  ['Standard', sizes.controlHeight.standard],
  ['Large', sizes.controlHeight.large],
] as const;

type GallerySectionProps = PropsWithChildren<{
  title: string;
  description?: string;
}>;

function GallerySection({ title, description, children }: GallerySectionProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        styles.section,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.borderSubtle,
        },
      ]}>
      <View style={styles.sectionHeader}>
        <Text
          accessibilityRole="header"
          style={[theme.typography.title, { color: theme.colors.textPrimary }]}>
          {title}
        </Text>
        {description ? (
          <Text style={[theme.typography.supporting, { color: theme.colors.textSecondary }]}>
            {description}
          </Text>
        ) : null}
      </View>
      {children}
    </View>
  );
}

type ColorSwatchProps = {
  label: string;
  value: string;
};

function ColorSwatch({ label, value }: ColorSwatchProps) {
  const theme = useTheme();

  return (
    <View
      accessible
      accessibilityLabel={`${label}: ${value}`}
      style={styles.swatchRow}>
      <View
        style={[
          styles.swatch,
          { backgroundColor: value, borderColor: theme.colors.borderSubtle },
        ]}
      />
      <View style={styles.swatchText}>
        <Text style={[theme.typography.body, { color: theme.colors.textPrimary }]}>{label}</Text>
        <Text
          style={[
            theme.typography.supporting,
            styles.colorValue,
            { color: theme.colors.textSecondary },
          ]}>
          {value}
        </Text>
      </View>
    </View>
  );
}

type StatusSampleProps = {
  symbol: string;
  label: string;
  message: string;
  palette: StatusColors;
};

function StatusSample({ symbol, label, message, palette }: StatusSampleProps) {
  const theme = useTheme();

  return (
    <View
      accessible
      accessibilityLabel={`${label}: ${message}`}
      style={[
        styles.statusSample,
        { backgroundColor: palette.subtle, borderColor: palette.border },
      ]}>
      <View style={[styles.statusSymbol, { backgroundColor: palette.main }]}>
        <Text
          importantForAccessibility="no"
          style={[theme.typography.buttonLabel, { color: palette.onMain }]}>
          {symbol}
        </Text>
      </View>
      <View style={styles.statusText}>
        <Text style={[theme.typography.body, { color: palette.onSubtle }]}>{label}</Text>
        <Text style={[theme.typography.supporting, { color: palette.onSubtle }]}>{message}</Text>
      </View>
    </View>
  );
}

function AppearanceSelector() {
  const theme = useTheme();
  const { preference, setPreference } = useThemePreference();
  const { colors } = theme;

  return (
    <View style={styles.appearanceGroup}>
      <Text style={[theme.typography.body, { color: colors.textPrimary }]}>Preview appearance</Text>
      <View
        accessibilityRole="radiogroup"
        style={[
          styles.appearanceSelector,
          { backgroundColor: colors.surfaceSubtle, borderColor: colors.borderSubtle },
        ]}>
        {appearanceOptions.map(([value, label]) => {
          const isSelected = preference === value;

          return (
            <Pressable
              key={value}
              accessibilityRole="radio"
              accessibilityState={{ checked: isSelected }}
              onPress={() => setPreference(value)}
              style={({ pressed }) => [
                styles.appearanceOption,
                {
                  backgroundColor: isSelected
                    ? colors.selection.subtle
                    : pressed
                      ? colors.surface
                      : colors.selection.unselectedBackground,
                  borderColor: isSelected
                    ? colors.selection.indicator
                    : colors.selection.unselectedBackground,
                },
              ]}>
              <Text
                style={[
                  theme.typography.supporting,
                  styles.appearanceOptionLabel,
                  {
                    color: isSelected ? colors.selection.content : colors.textSecondary,
                  },
                ]}>
                {isSelected ? `✓ ${label}` : label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export function FoundationGalleryScreen() {
  const theme = useTheme();
  const { colors } = theme;
  const adaptiveLayout = useAdaptiveLayout();

  const colorSamples = [
    ['Screen', colors.screen],
    ['Surface', colors.surface],
    ['Subtle surface', colors.surfaceSubtle],
    ['Primary text', colors.textPrimary],
    ['Secondary text', colors.textSecondary],
    ['Control border', colors.borderControl],
    ['Primary action', colors.brand.action],
    ['Content on primary action', colors.brand.onAction],
  ] as const;

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: colors.screen }]} edges={['top']}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[
          styles.content,
          { paddingHorizontal: adaptiveLayout.metrics.screenGutter },
        ]}
        showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.headerCopy}>
            <Text accessibilityRole="header" style={[theme.typography.title, { color: colors.textPrimary }]}>
              Foundation gallery
            </Text>
            <Text style={[theme.typography.body, { color: colors.textSecondary }]}>
              A development screen for checking Sarflog&apos;s design decisions on a real device.
            </Text>
          </View>
          <View
            accessible
            accessibilityLabel={`${theme.mode} appearance is active`}
            style={[
              styles.modeBadge,
              {
                backgroundColor: colors.selection.subtle,
                borderColor: colors.selection.indicator,
              },
            ]}>
            <Text style={[theme.typography.supporting, { color: colors.selection.content }]}>
              {theme.mode === 'dark' ? 'Dark mode' : 'Light mode'}
            </Text>
          </View>
          <AppearanceSelector />
          <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
            System follows your phone. Light and Dark are temporary gallery previews and reset after reload.
          </Text>
        </View>

        <GallerySection
          title="Adaptive layout"
          description="Native window-size classes respond to the space available to the app, not a device model.">
          <View style={styles.sampleGroup}>
            <Text style={[theme.typography.body, { color: colors.textPrimary }]}>
              Current window: {Math.round(adaptiveLayout.width)} x {Math.round(adaptiveLayout.height)}
            </Text>
            <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
              Width: {widthClassLabels[adaptiveLayout.widthClass]} / Height:{' '}
              {heightClassLabels[adaptiveLayout.heightClass]} / Gutter:{' '}
              {adaptiveLayout.metrics.screenGutter} / Pane gap: {adaptiveLayout.metrics.paneGap}
            </Text>
            <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
              Two-pane preference: {adaptiveLayout.prefersTwoPane ? 'yes' : 'no'}
            </Text>
          </View>
        </GallerySection>

        <GallerySection
          title="Typography"
          description="The four approved sizes and two bundled Inter weights.">
          <View style={styles.sampleGroup}>
            <View style={styles.typeSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                DISPLAY AMOUNT · 32/40 · SEMIBOLD 600
              </Text>
              <Text style={[theme.typography.displayAmount, { color: colors.textPrimary }]}>
                12 450 000 UZS
              </Text>
            </View>
            <View style={styles.typeSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                TITLE · 20/28 · SEMIBOLD 600
              </Text>
              <Text style={[theme.typography.title, { color: colors.textPrimary }]}>Monthly overview</Text>
            </View>
            <View style={styles.typeSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                BODY · 16/24 · REGULAR 400
              </Text>
              <Text style={[theme.typography.body, { color: colors.textPrimary }]}>
                You spent less than last month and remain inside your planned budget.
              </Text>
            </View>
            <View style={styles.typeSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                SUPPORTING · 13/18 · REGULAR 400
              </Text>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                Updated five minutes ago
              </Text>
            </View>
            <View style={styles.typeSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                BUTTON LABEL · 16/24 · SEMIBOLD 600
              </Text>
              <Text style={[theme.typography.buttonLabel, { color: colors.textPrimary }]}>Save expense</Text>
            </View>
          </View>
        </GallerySection>

        <GallerySection
          title="Buttons"
          description="HeroUI Native owns shape, label weight, and press feedback. Sarflog supplies the green and semantic colors.">
          <View style={styles.buttonGallery}>
            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>PRIMARY · MEDIUM</Text>
              <Button className="w-full" onPress={noop}>Add expense</Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>PRIMARY · LARGE</Text>
              <Button className="w-full" onPress={noop} size="lg">Save expense</Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>SECONDARY</Text>
              <Button className="w-full" onPress={noop} variant="secondary">Cancel</Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>OUTLINE</Text>
              <Button
                className={
                  useHeroWebFallback
                    ? 'w-full bg-transparent border border-border'
                    : 'w-full'
                }
                onPress={noop}
                variant={useHeroWebFallback ? 'tertiary' : 'outline'}>
                Set budget
              </Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>DESTRUCTIVE</Text>
              <Button className="w-full" onPress={noop} variant="danger">Delete expense</Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>GHOST</Text>
              <Button
                className={useHeroWebFallback ? 'w-full bg-transparent' : 'w-full'}
                onPress={noop}
                variant={useHeroWebFallback ? 'tertiary' : 'ghost'}>
                View details
              </Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>LOADING · BLOCKS REPEATED TAPS</Text>
              <Button
                accessibilityLabel="Saving expense"
                accessibilityState={{ busy: true, disabled: true }}
                className="w-full"
                isDisabled
                onPress={noop}>
                Saving…
              </Button>
            </View>

            <View style={styles.buttonSample}>
              <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>DISABLED</Text>
              <Button className="w-full" isDisabled onPress={noop}>Save expense</Button>
            </View>
          </View>
        </GallerySection>

        <GallerySection
          title="Core colors"
          description="Every sample is labeled because color must never carry meaning by itself.">
          <View style={styles.swatchGrid}>
            {colorSamples.map(([label, value]) => (
              <ColorSwatch key={label} label={label} value={value} />
            ))}
          </View>
        </GallerySection>

        <GallerySection
          title="Status families"
          description="Solid accents, subtle surfaces, readable content, and supplementary borders.">
          <View style={styles.statusGrid}>
            <StatusSample
              symbol="✓"
              label="Success"
              message="Expense saved"
              palette={colors.status.success}
            />
            <StatusSample
              symbol="!"
              label="Warning"
              message="Budget limit is close"
              palette={colors.status.warning}
            />
            <StatusSample
              symbol="i"
              label="Information"
              message="Exchange rate updated"
              palette={colors.status.information}
            />
            <StatusSample
              symbol="×"
              label="Destructive"
              message="Expense could not be saved"
              palette={colors.status.destructive}
            />
          </View>
        </GallerySection>

        <GallerySection
          title="Spacing"
          description="A 4-point base with an 8-point primary rhythm. Bar width is twice the token value.">
          <View style={styles.scaleGroup}>
            {spacingSamples.map(([name, value]) => (
              <View key={name} style={styles.scaleRow}>
                <View style={styles.scaleLabel}>
                  <Text style={[theme.typography.supporting, { color: colors.textPrimary }]}>{name}</Text>
                  <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>{value}</Text>
                </View>
                <View
                  accessible
                  accessibilityLabel={`${name} spacing: ${value}`}
                  style={[
                    styles.scaleBar,
                    { width: value * 2, backgroundColor: colors.selection.indicator },
                  ]}
                />
              </View>
            ))}
          </View>
        </GallerySection>

        <GallerySection
          title="Corner radii"
          description="Outer surfaces generally use equal or greater rounding than their contents.">
          <View style={styles.radiusGrid}>
            {radiusSamples.map(([name, value]) => (
              <View key={name} style={styles.radiusSample}>
                <View
                  accessible
                  accessibilityLabel={`${name} radius: ${value === radii.full ? 'fully rounded' : value}`}
                  style={[
                    styles.radiusShape,
                    {
                      backgroundColor: colors.surfaceSubtle,
                      borderColor: colors.borderControl,
                      borderRadius: value,
                    },
                  ]}
                />
                <Text style={[theme.typography.supporting, styles.radiusLabel, { color: colors.textPrimary }]}>
                  {name}
                </Text>
                <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>
                  {value === radii.full ? 'Full' : value}
                </Text>
              </View>
            ))}
          </View>
        </GallerySection>

        <GallerySection
          title="Control minimums"
          description="These are minimum heights. Text-containing controls may grow for accessibility.">
          <View style={styles.controlGroup}>
            {controlSamples.map(([name, value]) => (
              <View
                key={name}
                accessible
                accessibilityLabel={`${name} control: minimum height ${value}`}
                style={[
                  styles.controlSample,
                  {
                    minHeight: value,
                    backgroundColor: colors.surfaceSubtle,
                    borderColor: colors.borderControl,
                  },
                ]}>
                <Text style={[theme.typography.body, { color: colors.textPrimary }]}>{name}</Text>
                <Text style={[theme.typography.supporting, { color: colors.textSecondary }]}>{value}</Text>
              </View>
            ))}
          </View>
        </GallerySection>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    width: '100%',
    maxWidth: MaxContentWidth,
    alignSelf: 'center',
    paddingTop: spacing.lg,
    paddingBottom: BottomTabInset + spacing.xxxl,
    gap: spacing.lg,
  },
  header: {
    gap: spacing.md,
  },
  headerCopy: {
    gap: spacing.xs,
  },
  modeBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderWidth: 1,
    borderRadius: radii.full,
  },
  appearanceGroup: {
    gap: spacing.xs,
  },
  appearanceSelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: spacing.xxs,
    borderWidth: 1,
    borderRadius: radii.large,
    gap: spacing.xxs,
  },
  appearanceOption: {
    minWidth: 88,
    minHeight: sizes.touchTarget.minimumHeight,
    flexGrow: 1,
    flexBasis: 0,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderWidth: 1,
    borderRadius: radii.medium,
  },
  appearanceOptionLabel: {
    textAlign: 'center',
  },
  section: {
    padding: spacing.md,
    borderWidth: 1,
    borderRadius: radii.large,
    gap: spacing.lg,
  },
  sectionHeader: {
    gap: spacing.xxs,
  },
  sampleGroup: {
    gap: spacing.lg,
  },
  buttonGallery: {
    gap: spacing.lg,
  },
  buttonSample: {
    gap: spacing.xs,
  },
  typeSample: {
    gap: spacing.xxs,
  },
  swatchGrid: {
    gap: spacing.md,
  },
  swatchRow: {
    minHeight: sizes.touchTarget.minimumHeight,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  swatch: {
    width: sizes.touchTarget.minimumWidth,
    height: sizes.touchTarget.minimumHeight,
    borderWidth: 1,
    borderRadius: radii.medium,
  },
  swatchText: {
    flex: 1,
    gap: spacing.xxs,
  },
  colorValue: {
    fontFamily: fontFamilies.monospace,
  },
  statusGrid: {
    gap: spacing.sm,
  },
  statusSample: {
    minHeight: sizes.controlHeight.large,
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.sm,
    borderWidth: 1,
    borderRadius: radii.medium,
    gap: spacing.sm,
  },
  statusSymbol: {
    width: spacing.xl,
    height: spacing.xl,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.full,
  },
  statusText: {
    flex: 1,
    gap: spacing.xxs,
  },
  scaleGroup: {
    gap: spacing.sm,
  },
  scaleRow: {
    minHeight: spacing.xl,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  scaleLabel: {
    width: spacing.xxxl,
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.xs,
  },
  scaleBar: {
    height: spacing.xs,
    borderRadius: radii.full,
  },
  radiusGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.lg,
  },
  radiusSample: {
    width: spacing.xxxl,
    alignItems: 'center',
    gap: spacing.xxs,
  },
  radiusShape: {
    width: spacing.xxxl,
    height: spacing.xxxl,
    borderWidth: 1,
  },
  radiusLabel: {
    textAlign: 'center',
  },
  controlGroup: {
    gap: spacing.sm,
  },
  controlSample: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    borderWidth: 1,
    borderRadius: radii.medium,
    gap: spacing.md,
  },
});
