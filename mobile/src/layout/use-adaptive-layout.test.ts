import { responsiveLayoutMetrics } from './metrics';
import { getAdaptiveLayout } from './use-adaptive-layout';

function getLayout(width: number, height: number) {
  return getAdaptiveLayout({
    width,
    height,
    scale: 3,
    fontScale: 1,
  });
}

test('uses compact metrics for a phone-sized window', () => {
  const layout = getLayout(390, 844);

  expect(layout).toMatchObject({
    widthClass: 'compact',
    heightClass: 'regular',
    metrics: responsiveLayoutMetrics.compact,
    prefersTwoPane: false,
  });
});

test('uses two panes only when both width and height allow it', () => {
  const regularWindow = getLayout(900, 700);

  expect(regularWindow.prefersTwoPane).toBe(true);

  const shortWindow = getLayout(900, 400);

  expect(shortWindow).toMatchObject({
    widthClass: 'expanded',
    heightClass: 'compact',
    prefersTwoPane: false,
  });
});
