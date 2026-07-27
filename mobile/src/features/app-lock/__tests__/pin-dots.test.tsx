import { render, screen } from '@testing-library/react-native';
import { PinDots } from '../components/pin-dots';

// Mock useTheme
jest.mock('@/hooks/use-theme', () => ({
  useTheme: () => ({
    colors: {
      textPrimary: '#FFFFFF',
      borderSubtle: '#333333',
      brand: { action: '#22C55E', onAction: '#052E16' },
      status: { destructive: { main: '#EF4444' } },
    },
  }),
}));

describe('PinDots', () => {
  it('has correct accessibility label', async () => {
    await render(<PinDots count={2} maxDigits={5} />);
    expect(screen.getByLabelText(/PIN.*2.*5/)).toBeTruthy();
  });

  it('shows error state without crash', async () => {
    await render(<PinDots count={2} isError />);
    expect(screen.getByLabelText(/PIN.*2.*5/)).toBeTruthy();
  });
});
