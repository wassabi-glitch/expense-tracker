import { renderHook, act } from '@testing-library/react-native';
import { useNavigationTheme } from '@/hooks/use-navigation-theme';

describe('useNavigationTheme', () => {
  it('should have default preference as glass', async () => {
    const { result } = await renderHook(() => useNavigationTheme());
    expect(result.current.tabBarPreference).toBe('glass');
  });

  it('should allow setting the preference', async () => {
    const { result } = await renderHook(() => useNavigationTheme());

    await act(() => {
      result.current.setTabBarPreference('solid');
    });

    expect(result.current.tabBarPreference).toBe('solid');

    await act(() => {
      result.current.setTabBarPreference('glass');
    });

    expect(result.current.tabBarPreference).toBe('glass');
  });
});
