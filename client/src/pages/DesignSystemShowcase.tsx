import { useState } from 'react';
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Input,
  Textarea,
  Badge,
  Select,
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogFooter,
  DialogCloseButton,
  ThemeToggle,
  ThemeSelector,
} from '@/components/ui-new';

/**
 * Design System Showcase Page
 * Professional documentation and component gallery for the CreditNexus UI Library
 */
export function DesignSystemShowcase() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [selectValue, setSelectValue] = useState('');

  const selectOptions = [
    { value: '', label: 'Select an option...' },
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
    { value: 'option3', label: 'Option 3', disabled: true },
    { value: 'option4', label: 'Option 4' },
  ];

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-700/50 bg-slate-900/95 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">CreditNexus Design System</h1>
              <p className="text-sm text-slate-400">Professional Fintech UI Components</p>
            </div>
            <div className="flex items-center gap-4">
              <ThemeSelector />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Introduction */}
        <section className="mb-12">
          <Card variant="primary">
            <CardHeader>
              <CardTitle>Overview</CardTitle>
              <CardDescription>
                A comprehensive collection of modern, accessible UI components built with React, TypeScript, and Tailwind CSS.
                Designed for fintech applications with a focus on trust, clarity, and professional aesthetics.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                  <h3 className="font-semibold text-white mb-1">Accessible</h3>
                  <p className="text-sm text-slate-400">ARIA labels, keyboard navigation, and screen reader support</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                  <h3 className="font-semibold text-white mb-1">Themeable</h3>
                  <p className="text-sm text-slate-400">Light, dark, and system theme support with CSS variables</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                  <h3 className="font-semibold text-white mb-1">Type-Safe</h3>
                  <p className="text-sm text-slate-400">Full TypeScript support with comprehensive prop types</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Buttons Section */}
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">Buttons</h2>
              <p className="text-sm text-slate-400">Interactive button components with multiple variants and sizes</p>
            </div>
            <ThemeToggle />
          </div>

          <div className="grid gap-6">
            {/* Variants */}
            <Card>
              <CardHeader>
                <CardTitle>Variants</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4">
                  <Button variant="primary">Primary</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="ghost">Ghost</Button>
                  <Button variant="danger">Danger</Button>
                  <Button variant="outline">Outline</Button>
                </div>
              </CardContent>
            </Card>

            {/* Sizes */}
            <Card>
              <CardHeader>
                <CardTitle>Sizes</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center gap-4">
                  <Button size="sm">Small</Button>
                  <Button size="md">Medium</Button>
                  <Button size="lg">Large</Button>
                  <Button size="icon">
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* States */}
            <Card>
              <CardHeader>
                <CardTitle>States</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-4">
                  <Button loading>Loading</Button>
                  <Button disabled>Disabled</Button>
                  <Button variant="secondary" loading>Loading</Button>
                  <Button variant="secondary" disabled>Disabled</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Cards Section */}
        <section className="mb-12">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white">Cards</h2>
            <p className="text-sm text-slate-400">Container components for organizing content with visual hierarchy</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card variant="primary">
              <CardHeader>
                <CardTitle>Primary Card</CardTitle>
                <CardDescription>High emphasis with accent border</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-slate-300">Use for critical information and primary actions.</p>
              </CardContent>
              <CardFooter>
                <Button size="sm">Action</Button>
              </CardFooter>
            </Card>

            <Card variant="secondary">
              <CardHeader>
                <CardTitle>Secondary Card</CardTitle>
                <CardDescription>Medium emphasis container</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-slate-300">Use for supporting information and grouped content.</p>
              </CardContent>
              <CardFooter>
                <Button variant="secondary" size="sm">Action</Button>
              </CardFooter>
            </Card>

            <Card variant="glass">
              <CardHeader>
                <CardTitle>Glass Card</CardTitle>
                <CardDescription>Glassmorphism effect</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-slate-300">Use for overlays and floating elements.</p>
              </CardContent>
              <CardFooter>
                <Button variant="ghost" size="sm">Action</Button>
              </CardFooter>
            </Card>

            <Card variant="interactive">
              <CardHeader>
                <CardTitle>Interactive Card</CardTitle>
                <CardDescription>Clickable with hover effects</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-slate-300">Use for clickable cards and navigation elements.</p>
              </CardContent>
            </Card>

            <Card variant="tertiary">
              <CardHeader>
                <CardTitle>Tertiary Card</CardTitle>
                <CardDescription>Low emphasis background</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-slate-300">Use for background containers and grouping.</p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Form Elements Section */}
        <section className="mb-12">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white">Form Elements</h2>
            <p className="text-sm text-slate-400">Input fields, textareas, and select components</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Input Fields</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  label="Default Input"
                  placeholder="Enter text..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                />
                <Input
                  label="With Helper Text"
                  placeholder="Enter text..."
                  helperText="This is a helpful description"
                />
                <Input
                  label="Error State"
                  placeholder="Enter text..."
                  error="This field is required"
                />
                <Input
                  label="Disabled"
                  placeholder="Cannot edit"
                  disabled
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Select & Textarea</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select
                  label="Select Dropdown"
                  options={selectOptions}
                  value={selectValue}
                  onChange={(e) => setSelectValue(e.target.value)}
                  placeholder="Choose an option"
                />
                <Select
                  label="With Error"
                  options={selectOptions}
                  error="Please select a valid option"
                />
                <Textarea
                  label="Textarea"
                  placeholder="Enter longer text..."
                  rows={3}
                />
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Badges Section */}
        <section className="mb-12">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white">Badges</h2>
            <p className="text-sm text-slate-400">Status indicators and labels</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Variants & Sizes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="flex flex-wrap gap-3">
                  <Badge>Default</Badge>
                  <Badge variant="primary">Primary</Badge>
                  <Badge variant="success">Success</Badge>
                  <Badge variant="warning">Warning</Badge>
                  <Badge variant="error">Error</Badge>
                  <Badge variant="info">Info</Badge>
                </div>
                <div className="flex flex-wrap gap-3 items-center">
                  <Badge size="sm">Small</Badge>
                  <Badge size="md">Medium</Badge>
                  <Badge size="lg">Large</Badge>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Badge icon={<svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>}>With Icon</Badge>
                  <Badge variant="success" icon={<svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>}>Completed</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Dialog Section */}
        <section className="mb-12">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white">Dialog</h2>
            <p className="text-sm text-slate-400">Modal overlays with focus trap and keyboard navigation</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Dialog Demo</CardTitle>
              <CardDescription>Click the button to open a dialog</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <Button onClick={() => setDialogOpen(true)}>Open Dialog</Button>
              </div>
            </CardContent>
          </Card>

          {/* Dialog Component */}
          <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} size="md">
            <DialogHeader>
              <div className="flex items-start justify-between">
                <div>
                  <DialogTitle>Confirm Action</DialogTitle>
                  <DialogDescription>
                    Are you sure you want to proceed with this action? This cannot be undone.
                  </DialogDescription>
                </div>
                <DialogCloseButton onClose={() => setDialogOpen(false)} />
              </div>
            </DialogHeader>
            <DialogContent>
              <div className="space-y-4">
                <Input
                  label="Reason (Optional)"
                  placeholder="Enter your reason..."
                />
                <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
                  <div className="flex gap-3">
                    <svg className="h-5 w-5 text-amber-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                      <h4 className="font-medium text-amber-400">Warning</h4>
                      <p className="text-sm text-amber-300/80 mt-1">
                        This action will permanently affect your account settings.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </DialogContent>
            <DialogFooter>
              <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => setDialogOpen(false)}>
                Confirm
              </Button>
            </DialogFooter>
          </Dialog>
        </section>

        {/* Code Examples Section */}
        <section className="mb-12">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-white">Code Examples</h2>
            <p className="text-sm text-slate-400">Quick start with component usage patterns</p>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Import Components</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 overflow-x-auto">
                  <code className="text-sm text-slate-300">
{`import { 
  Button, 
  Card, 
  Input, 
  Badge,
  ThemeProvider,
  useTheme 
} from '@/components/ui-new';`}
                  </code>
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Button Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 overflow-x-auto">
                  <code className="text-sm text-slate-300">
{`<Button variant="primary" size="md" loading={isLoading}>
  Submit
</Button>

<Button variant="secondary" onClick={handleCancel}>
  Cancel
</Button>

<Button variant="danger" disabled={!canDelete}>
  Delete
</Button>`}
                  </code>
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Card Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 overflow-x-auto">
                  <code className="text-sm text-slate-300">
{`<Card variant="primary">
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Card content goes here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>`}
                  </code>
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Theme Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="p-4 rounded-lg bg-slate-950 border border-slate-800 overflow-x-auto">
                  <code className="text-sm text-slate-300">
{`// In your app root
<ThemeProvider>
  <App />
</ThemeProvider>

// In a component
const { theme, resolvedTheme, setTheme } = useTheme();

// Toggle theme
setTheme('dark'); // 'light' | 'dark' | 'system'

// Pre-built toggle
<ThemeToggle />

// Pre-built selector
<ThemeSelector />`}
                  </code>
                </pre>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-700/50 pt-8 mt-16">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <p>CreditNexus Design System v1.0.0</p>
            <p>Built with React + TypeScript + Tailwind CSS</p>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default DesignSystemShowcase;
