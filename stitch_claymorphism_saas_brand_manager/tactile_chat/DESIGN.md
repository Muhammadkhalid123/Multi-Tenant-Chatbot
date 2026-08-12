---
name: Tactile Chat
colors:
  surface: '#fbf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fbf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae8e7'
  surface-container-highest: '#e4e2e1'
  on-surface: '#1b1c1c'
  on-surface-variant: '#454652'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0f0'
  outline: '#757684'
  outline-variant: '#c5c5d4'
  surface-tint: '#4156ba'
  primary: '#4156ba'
  on-primary: '#ffffff'
  primary-container: '#7b8ff7'
  on-primary-container: '#002088'
  inverse-primary: '#b9c3ff'
  secondary: '#4a6545'
  on-secondary: '#ffffff'
  secondary-container: '#c9e8bf'
  on-secondary-container: '#4f6a49'
  tertiary: '#845238'
  on-tertiary: '#ffffff'
  tertiary-container: '#c4896b'
  on-tertiary-container: '#4c240e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dee1ff'
  primary-fixed-dim: '#b9c3ff'
  on-primary-fixed: '#001159'
  on-primary-fixed-variant: '#263ca1'
  secondary-fixed: '#ccebc2'
  secondary-fixed-dim: '#b1cfa7'
  on-secondary-fixed: '#082007'
  on-secondary-fixed-variant: '#334d2f'
  tertiary-fixed: '#ffdbcb'
  tertiary-fixed-dim: '#f9b898'
  on-tertiary-fixed: '#331101'
  on-tertiary-fixed-variant: '#683b23'
  background: '#fbf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e1'
typography:
  headline-xl:
    fontFamily: Quicksand
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Quicksand
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Quicksand
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Quicksand
    fontSize: 18px
    fontWeight: '500'
    lineHeight: '1.6'
  body-md:
    fontFamily: Quicksand
    fontSize: 16px
    fontWeight: '500'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Quicksand
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: 0.01em
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  unit: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style
The design system focuses on a friendly, approachable, and highly tactile aesthetic tailored for a modern Chatbot SaaS. The brand personality is helpful, optimistic, and soft, moving away from the cold, flat corporate standards of traditional software. 

The visual style is **Claymorphism**. It utilizes soft, puffy, 3D-inflated surfaces that invite interaction. The interface should feel like physical objects resting on a soft surface, using dual inner and outer shadows to create a sense of volume without the use of complex gradients or skeuomorphic textures. The target audience is modern startups and creative teams looking for a tool that feels human and expressive.

## Colors
The palette is built upon a soft pastel base to maintain a "clay-like" appearance.

- **Primary (Periwinkle Blue):** Used for primary call-to-actions, brand accents, and active chat states.
- **Secondary (Sage Green):** Indicates success, active status, or bot "online" indicators.
- **Tertiary (Soft Amber):** Reserved for pending states, warnings, or premium features.
- **Error (Dusty Rose):** Used for destructive actions, errors, or "offline" states.
- **Neutral (Charcoal):** High-contrast text color to ensure legibility against pastel backgrounds.
- **Background:** A specific off-white lavender (#EEF0F7) that provides enough depth for white inner shadows to remain visible.

## Typography
This design system utilizes **Quicksand** exclusively to reinforce the soft, rounded aesthetic. The rounded terminals of the typeface mirror the high border-radius of the UI components.

- **Headlines:** Use Bold (700) or SemiBold (600) weights with slightly tighter letter spacing to maintain a "chunky" and impactful look.
- **Body:** Medium (500) weight is preferred over Regular to ensure text remains legible and substantial against the soft, shadowed backgrounds.
- **Labels:** Use SemiBold for navigation items and button labels to provide clear hierarchy.

## Layout & Spacing
The layout follows a "puffy" philosophy with generous negative space to prevent the 3D effects from feeling cluttered.

- **Grid:** 12-column fluid grid for desktop with wide 24px gutters.
- **Container Padding:** Use `lg` (40px) or `xl` (64px) for main dashboard sections to emphasize the floating nature of the claymorphic cards.
- **Gaps:** Use `md` (24px) for spacing between cards and large UI elements to allow shadows to breathe and not overlap awkwardly.
- **Mobile:** Transition to a single-column layout with 16px margins; reduce component padding slightly but maintain the high border-radius.

## Elevation & Depth
Depth is the defining characteristic of this design system. It is achieved through a specific "Claymorphism" shadow stack rather than standard elevation levels.

- **Outer Shadows:** Every container and button must have a dual shadow:
    1. **Light Shadow:** `top-left`, Color: `rgba(255, 255, 255, 0.6)`, Blur: `20px`, Spread: `0px`.
    2. **Dark Shadow:** `bottom-right`, Color: `rgba(0, 0, 0, 0.15)`, Blur: `25px`, Spread: `0px`.
- **Inner Shadows (Optional but recommended):** For a more "inflated" look, apply a subtle white inner shadow on the top-left edge and a darker inner shadow on the bottom-right edge of elements.
- **Hover State:** On hover, the dark shadow's blur should increase and the element should scale slightly (1.02x) to simulate the object lifting off the surface.

## Shapes
Shapes are exaggerated and organic. Hard corners are strictly prohibited.

- **Containers/Cards:** Use a border-radius between `20px` and `28px`.
- **Buttons/Inputs:** Use "Pill" shapes (`999px`) to create a soft, touchable feel.
- **Active States:** When a list item or navigation link is active, it should adopt the claymorphic card style (white background with the dual shadow) rather than just a color change.

## Components
- **Buttons:** Large, pill-shaped, and substantial. Primary buttons use Periwinkle Blue with white text. They should appear "inflated" via the dual shadow system.
- **Chat Bubbles:** The user's bubble should be white with standard claymorphic shadows; the bot's bubble should be Periwinkle Blue with a modified shadow (using a darker blue tint for the bottom shadow instead of black).
- **Input Fields:** Pill-shaped with a subtle "inset" shadow to appear slightly recessed into the background, then switching to an "outset" claymorphic look when focused.
- **Cards:** Used for analytics, user profiles, and bot settings. Always feature the background color of white or extremely light lavender to contrast against the #EEF0F7 base.
- **Chips/Badges:** Small, pill-shaped elements using the Sage, Amber, or Rose palettes with 50% opacity backgrounds and full-opacity text of the same hue.
- **Avatars:** Always circular, with a 2px white border and a soft outer shadow to separate them from chat bubbles.