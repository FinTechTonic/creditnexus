/**
 * UI Component Library - New Design System
 * CreditNexus Professional Fintech Components
 * 
 * @module ui-new
 * @version 1.0.0
 */

// Core Components
export { Button, buttonVariants, type ButtonProps } from "./button"
export { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent, 
  CardFooter,
  cardVariants,
  type CardProps 
} from "./card"
export { Input, Textarea, inputVariants, type InputProps, type TextareaProps } from "./input"

// New Components
export { Badge, badgeVariants, type BadgeProps } from "./badge"
export { Select, selectVariants, type SelectProps, type SelectOption } from "./select"
export {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogFooter,
  DialogCloseButton,
  dialogVariants,
  type DialogProps,
} from "./dialog"

// Theme Provider
export {
  ThemeProvider,
  useTheme,
  ThemeToggle,
  ThemeSelector,
} from "./theme-provider"

// Utility
export { cn } from "./button"
