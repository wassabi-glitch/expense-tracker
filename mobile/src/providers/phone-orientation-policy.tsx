// Dynamically imported to prevent crashing on stale development builds missing the native module.
/* eslint-disable @typescript-eslint/no-unused-vars, @typescript-eslint/no-require-imports */
import { useEffect } from 'react';
import { Platform, useWindowDimensions } from 'react-native';
let ScreenOrientation: any = null;
try {
  ScreenOrientation = require('expo-screen-orientation');
} catch (e) {
  console.warn('expo-screen-orientation native module missing, rotation lock disabled.');
}

/**
 * Android's compact-window boundary. If either dimension is below this value,
 * the device is treated as phone-sized for the orientation policy.
 */
export const largeScreenMinimumDimension = 600;

export function shouldLockPhonePortrait(width: number, height: number): boolean {
  return Math.min(width, height) < largeScreenMinimumDimension;
}

/**
 * Keeps compact phones portrait while allowing tablets and unfolded large
 * screens to follow the user's orientation preference.
 */
export function PhoneOrientationPolicy() {
  const { width, height } = useWindowDimensions();
  const shouldLockPortrait = shouldLockPhonePortrait(width, height);

  useEffect(() => {
    if (Platform.OS === 'web') {
      return;
    }

    const applyPolicy = (shouldLockPortrait && ScreenOrientation)
      ? ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.PORTRAIT_UP)
      : (ScreenOrientation ? ScreenOrientation.unlockAsync() : Promise.resolve());

    void applyPolicy.catch((error: unknown) => {
      if (__DEV__) {
        console.warn('Unable to apply the phone orientation policy.', error);
      }
    });
  }, [shouldLockPortrait]);

  return null;
}
