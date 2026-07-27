import { WebView } from 'react-native-webview';
import { View, StyleSheet, Platform } from 'react-native';

export type TurnstileWebViewProps = {
  siteKey: string;
  onSuccess: (token: string) => void;
};

export function TurnstileWebView({ siteKey, onSuccess }: TurnstileWebViewProps) {
  if (Platform.OS === 'web') {
    // Usually shouldn't render this on web, but fallback gracefully
    return null;
  }

  const html = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
      <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" async defer></script>
      <style>
        body {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100vh;
          margin: 0;
          background-color: transparent;
        }
      </style>
    </head>
    <body>
      <div id="turnstile-widget"></div>
      <script>
        window.onload = function() {
          turnstile.render('#turnstile-widget', {
            sitekey: '${siteKey}',
            callback: function(token) {
              window.ReactNativeWebView.postMessage(token);
            },
          });
        };
      </script>
    </body>
    </html>
  `;

  return (
    <View style={styles.container}>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        onMessage={(event) => {
          const token = event.nativeEvent.data;
          if (token) {
            onSuccess(token);
          }
        }}
        scrollEnabled={false}
        bounces={false}
        style={styles.webview}
        containerStyle={styles.webviewContainer}
        showsHorizontalScrollIndicator={false}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: 80,
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  webviewContainer: {
    backgroundColor: 'transparent',
    flex: 1,
  },
  webview: {
    backgroundColor: 'transparent',
    opacity: 0.99, // Fixes an issue on some Android devices where transparent webview doesn't render properly
  },
});
