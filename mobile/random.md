1. Establish the design decisions
   Before organizing files, decide the small vocabulary Sarflog needs:
   Brand color
   Neutral colors
   Light and dark backgrounds
   Text hierarchy
   Typography scale
   Spacing scale
   Corner radii
   Control sizes
   Shadows/elevation
   Motion durations
   Accessibility requirements
   This prevents us from creating arbitrary tokens merely because other design systems have them.

2. Define primitive tokens
   These are the raw ingredients:
   brand green
   neutral 50
   neutral 100
   neutral 900
   spacing 4
   spacing 8
   spacing 12
   radius 8
   radius 12
   Primitive names describe the value, not its purpose.
3. Define semantic tokens
   Next, assign meaning:
   Raw value Semantic purpose

Sarflog green → action primary
Neutral 900 → primary text
Neutral 500 → secondary text
Neutral 100 → subtle border
White → screen background
Components should consume semantic roles. A Button should request action primary, not directly request Sarflog green. 4. Create light and dark themes
Each theme resolves the same semantic roles differently:
Semantic role Light Dark

screen background white near black
card surface white dark surface
primary text near black near white
subtle border light neutral dark neutral
primary action Sarflog green Sarflog green
Both modes expose the same vocabulary, so components do not contain theme-specific decisions. 5. Add the ThemeProvider
Only after the theme shape is understood should the provider:
Detect light or dark mode
Expose the resolved semantic theme
React when system appearance changes
Potentially support a future user preference
The provider belongs under providers, while the actual design values belong under theme. 6. Build the first UI primitives
Then validate the foundation through a deliberately small set:
Text
Button
Input
Card or Surface
IconButton
Screen container
These expose missing tokens quickly. For example, building Input may reveal that focus, error, placeholder and disabled colors have not yet been defined. 7. Validate before making screens
A temporary component-gallery screen can test:
Light and dark themes
Android and iOS
Small and large text
Pressed, disabled, loading and error states
Long labels
Touch-target sizes
Safe areas
Shadows and Android elevation
Only after that foundation feels coherent should feature screens consume it.
