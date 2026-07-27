/**
 * Expo resolves packages with the `react-native` export condition. MSW
 * intentionally disables `msw/node` for that condition, while Jest tests need
 * its Node interceptor. Override conditions for that one documented subpath.
 */
module.exports = (request, options) => {
  if (request === 'msw/node') {
    return options.defaultResolver(request, {
      ...options,
      conditions: ['node', 'require', 'default'],
    });
  }

  return options.defaultResolver(request, options);
};
