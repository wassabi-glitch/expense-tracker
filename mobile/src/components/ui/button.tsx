import { Button as HeroButton, useButton } from 'heroui-native/button';
import type {
  ButtonContextValue,
  ButtonLabelProps,
  ButtonRootProps,
  ButtonSize,
  ButtonVariant,
} from 'heroui-native/button';
import { forwardRef } from 'react';
/* eslint-disable @typescript-eslint/no-unused-vars */
import type { ElementRef } from 'react';
import { View } from 'react-native';

const ButtonRoot = forwardRef<ElementRef<typeof View>, ButtonRootProps>(
  ({ children, className, ...props }, ref) => {
    // 1. Determine if this button should get the filled-disabled treatment
    const isFilled = props.variant === 'primary' || props.variant === 'danger' || props.variant === undefined;

    // We only inject our interceptor for string children, but we no longer override
    // the root opacity or background because the user wants to retain the brand colors.
    let content = children;
    if (typeof children === 'string' || typeof children === 'number') {
      content = <ButtonLabel>{children}</ButtonLabel>;
    }

    return (
      <HeroButton
        ref={ref as any}
        className={className}
        {...props}
      >
        {content}
      </HeroButton>
    );
  }
);
ButtonRoot.displayName = 'Button';

function ButtonLabel({ className, style, ...props }: ButtonLabelProps) {
  const { isDisabled, variant } = useButton();

  const isFilled = variant === 'primary' || variant === 'danger' || variant === undefined;

  // 4. Use crisp black text that is readable but not overly harsh
  const disabledLabelClass = (isDisabled && isFilled) ? 'text-black' : '';

  return (
    <HeroButton.Label
      className={[disabledLabelClass, className].filter(Boolean).join(' ')}
      style={style}
      {...props}
    />
  );
}
ButtonLabel.displayName = 'Button.Label';

export const Button = Object.assign(ButtonRoot, {
  Label: ButtonLabel,
});

export { useButton };
export type {
  ButtonContextValue,
  ButtonLabelProps,
  ButtonRootProps,
  ButtonSize,
  ButtonVariant,
};
