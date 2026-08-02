import React, { forwardRef, createContext, useContext } from 'react';
import { View } from 'react-native';
import { Spinner } from 'heroui-native/spinner';
import { Button, useButton, type ButtonLabelProps } from './button';
import { useTheme } from '@/hooks/use-theme';

export type AppButtonProps = React.ComponentProps<typeof Button> & {
  isLoading?: boolean;
};

// Context to share the calculated text color with icons/spinners
const AppButtonContext = createContext<{ labelColor: string | undefined }>({ labelColor: undefined });

const AppButtonRoot = forwardRef<React.ElementRef<typeof View>, AppButtonProps>(
  ({ className, isLoading, isDisabled, children, ...props }, ref) => {
    const theme = useTheme();
    const variant = props.variant || 'primary';

    let labelColor: string | undefined;

    if (variant === 'primary') {
      labelColor = theme.colors.brand.onAction;
    } else if (variant === 'danger') {
      labelColor = theme.colors.status.destructive.onMain;
    } else if (variant === 'secondary') {
      labelColor = theme.colors.brand.action;
    } else if (['tertiary', 'outline', 'ghost'].includes(variant)) {
      labelColor = theme.colors.textPrimary;
    } else if (variant === 'danger-soft') {
      labelColor = theme.colors.status.destructive.main;
    }

    return (
      <AppButtonContext.Provider value={{ labelColor }}>
        <Button
          ref={ref}
          className={['rounded-xl flex-row items-center justify-center', className].filter(Boolean).join(' ')}
          isDisabled={isLoading || isDisabled}
          animation={isLoading ? ({ scale: false, highlight: false } as any) : undefined}
          {...props}
        >
          {isLoading ? (
            <View className="flex-row items-center justify-center gap-2">
              <Spinner size="sm" color={labelColor} />
              {typeof children === 'string' || typeof children === 'number' ? (
                <AppButtonLabel>{children}</AppButtonLabel>
              ) : (
                children
              )}
            </View>
          ) : (
            typeof children === 'string' || typeof children === 'number' ? (
              <AppButtonLabel>{children}</AppButtonLabel>
            ) : (
              children
            )
          )}
        </Button>
      </AppButtonContext.Provider>
    );
  }
);
AppButtonRoot.displayName = 'AppButton';

const AppButtonLabel = ({ style, ...props }: ButtonLabelProps) => {
  const { labelColor } = useContext(AppButtonContext);
  const { isDisabled } = useButton(); // Access parent button state

  return (
    <Button.Label
      style={[
        { textAlign: 'center' },
        (labelColor && !isDisabled) ? { color: labelColor } : undefined,
        style,
      ]}
      {...props}
    />
  );
};
AppButtonLabel.displayName = 'Button.Label';

export const AppButton = Object.assign(AppButtonRoot, {
  Label: AppButtonLabel,
});
