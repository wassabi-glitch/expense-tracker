import React from 'react';
import Svg, { Path } from 'react-native-svg';

interface Props {
  size?: number;
  color?: string;
  weight?: 'regular' | 'fill';
}

export function PhosphorHouse({ size = 24, color = 'black', weight = 'regular' }: Props) {
  // Phosphor icons have generous internal padding in their 256x256 viewBox.
  // We multiply the requested size by ~1.15 so it optically matches the height/width of other 24px icons (like Ionicons).
  const opticalSize = size * 1.15;
  
  return (
    <Svg width={opticalSize} height={opticalSize} viewBox="0 0 256 256" fill={color}>
      {weight === 'fill' ? (
        <Path d="M224,115.55V208a16,16,0,0,1-16,16H160a16,16,0,0,1-16-16V160a8,8,0,0,0-8-8H120a8,8,0,0,0-8,8v48a16,16,0,0,1-16,16H48a16,16,0,0,1-16-16V115.55a16,16,0,0,1,5.17-11.78l80-75.48.11-.11a16,16,0,0,1,21.53,0,1.14,1.14,0,0,0,.11.11l80,75.48A16,16,0,0,1,224,115.55Z" />
      ) : (
        <Path d="M224,115.55V208a16,16,0,0,1-16,16H160a16,16,0,0,1-16-16V160a8,8,0,0,0-8-8H120a8,8,0,0,0-8,8v48a16,16,0,0,1-16,16H48a16,16,0,0,1-16-16V115.55a16,16,0,0,1,5.17-11.78l80-75.48.11-.11a16,16,0,0,1,21.53,0,1.14,1.14,0,0,0,.11.11l80,75.48A16,16,0,0,1,224,115.55Zm-16,3.92L128,44,48,119.47V208H96V160a24,24,0,0,1,24-24h16a24,24,0,0,1,24,24v48h48Z" />
      )}
    </Svg>
  );
}
