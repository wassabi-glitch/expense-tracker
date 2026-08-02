import React, { forwardRef } from 'react';
import { View, type ViewProps } from 'react-native';

// --- Card Root ---
export interface CardProps extends ViewProps {
  variant?: 'flat' | 'elevated' | 'bordered';
}

const CardRoot = forwardRef<View, CardProps>(
  ({ className, variant = 'flat', style, ...props }, ref) => {
    // We enforce rounded-2xl (16px) globally.
    // We default to transparent background for the flat look, but can expand this later.
    const baseClasses = "rounded-2xl overflow-hidden";
    
    return (
      <View
        ref={ref}
        className={[baseClasses, className].filter(Boolean).join(' ')}
        style={[{ backgroundColor: 'transparent' }, style]}
        {...props}
      />
    );
  }
);
CardRoot.displayName = 'Card';

// --- Card Header ---
export interface CardHeaderProps extends ViewProps {}
const CardHeader = forwardRef<View, CardHeaderProps>(
  ({ className, ...props }, ref) => (
    <View ref={ref} className={['px-4 py-3', className].filter(Boolean).join(' ')} {...props} />
  )
);
CardHeader.displayName = 'Card.Header';

// --- Card Body ---
export interface CardBodyProps extends ViewProps {
  noPadding?: boolean;
}
const CardBody = forwardRef<View, CardBodyProps>(
  ({ className, noPadding = false, ...props }, ref) => (
    <View ref={ref} className={[noPadding ? '' : 'p-4', className].filter(Boolean).join(' ')} {...props} />
  )
);
CardBody.displayName = 'Card.Body';

// --- Card Footer ---
export interface CardFooterProps extends ViewProps {}
const CardFooter = forwardRef<View, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <View ref={ref} className={['px-4 py-3', className].filter(Boolean).join(' ')} {...props} />
  )
);
CardFooter.displayName = 'Card.Footer';

// Assemble the compound component
export const Card = Object.assign(CardRoot, {
  Header: CardHeader,
  Body: CardBody,
  Footer: CardFooter,
});
