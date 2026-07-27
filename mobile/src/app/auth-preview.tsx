import { Redirect } from 'expo-router';
import { AuthPreviewScreen } from '@/features/auth/preview/auth-preview-screen';

/**
 * Dev-only auth preview.  Redirects to home in production builds.
 */
export default function AuthPreviewRoute() {
  if (!__DEV__) {
    return <Redirect href="/" />;
  }

  return <AuthPreviewScreen />;
}
