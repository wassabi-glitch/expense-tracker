export type ThemeMode = 'light' | 'dark';
export type ThemePreference = ThemeMode | 'system';

export type ButtonStateColors = {
  background: string;
  content: string;
};

export type ButtonVariantColors = {
  default: ButtonStateColors;
  pressed: ButtonStateColors;
  loading: ButtonStateColors;
  focusOutline: string;
};

export type GhostButtonColors = ButtonVariantColors & {
  disabled: ButtonStateColors;
};

export type StatusColors = {
  main: string;
  onMain: string;
  subtle: string;
  onSubtle: string;
  border: string;
};

export type ThemeColors = {
  screen: string;
  surface: string;
  surfaceSubtle: string;
  surfacePressed: string;
  textPrimary: string;
  textSecondary: string;
  borderSubtle: string;
  borderControl: string;
  brand: {
    action: string;
    onAction: string;
  };
  status: {
    destructive: StatusColors;
    success: StatusColors;
    warning: StatusColors;
    information: StatusColors;
  };
  button: {
    filledDisabled: ButtonStateColors;
    primary: ButtonVariantColors;
    secondary: ButtonVariantColors;
    destructive: ButtonVariantColors;
    ghost: GhostButtonColors;
  };
  selection: {
    indicator: string;
    onIndicator: string;
    subtle: string;
    content: string;
    unselectedBackground: string;
    unselectedBorder: string;
  };
};

export type ThemeTextColorRole = 'textPrimary' | 'textSecondary' | 'selectionContent';

export type ThemeSurfaceColorRole = 'screen' | 'surface' | 'surfaceSubtle' | 'selectionSubtle';
