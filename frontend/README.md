# AI Chief-of-Staff Frontend

Next.js frontend for the AI Chief-of-Staff POC with TypeScript, Tailwind CSS, and Framer Motion.

## Features

- 📱 **Responsive Design**: Desktop-first with mobile support
- ⌨️ **Keyboard Shortcuts**: Cmd/Ctrl+K command palette, G I/T navigation
- 🎨 **Modern UI**: Tailwind CSS with dark mode support
- ✨ **Animations**: Framer Motion for smooth transitions
- ♿ **Accessible**: Semantic HTML, ARIA labels, keyboard navigation
- 🧠 **Offline Mode**: Supports local LLM and dummy inbox

## Quick Start

### Prerequisites

- Node.js >= 18
- Backend server running on http://localhost:3000 (or run `./scripts/run_local_demo.sh`)

### Installation

```bash
cd frontend
yarn install
# or
npm install
```

### Development

```bash
yarn dev
# or
npm run dev
```

Open http://localhost:3000 in your browser.

### Build for Production

```bash
yarn build
yarn start
```

## Project Structure

```
frontend/
├── app/                    # Next.js app router pages
│   ├── inbox/             # Inbox list view
│   ├── thread/[id]/      # Thread detail view
│   ├── tasks/            # Tasks page
│   ├── drafts/           # Drafts page
│   └── settings/         # Settings page
├── components/           # React components
│   ├── Sidebar.tsx       # Navigation sidebar
│   ├── InboxList.tsx     # Message list
│   ├── ThreadView.tsx    # Thread conversation
│   ├── SuggestionPanel.tsx # AI suggestion UI
│   ├── CommandPalette.tsx  # Cmd+K palette
│   └── ...
├── lib/                  # Utilities and hooks
│   ├── api.ts            # Backend API client
│   ├── hooks/            # Custom React hooks
│   └── utils.ts          # Helper functions
└── styles/               # Global styles
    └── globals.css       # Tailwind + custom CSS
```

## Keyboard Shortcuts

- **Cmd/Ctrl + K**: Open command palette
- **G I**: Go to Inbox
- **G T**: Go to Tasks
- **Shift + Enter**: Send reply (in suggestion editor)
- **Esc**: Close command palette / dialogs
- **↑↓**: Navigate command palette

## API Integration

The frontend communicates with the backend via:

- `GET /api/messages` - List messages
- `GET /api/messages/:id` - Get thread
- `POST /api/messages/:id/generate` - Generate AI suggestion
- `POST /api/messages/:id/send` - Send reply
- `GET /api/health/local` - Check offline mode status

See `lib/api.ts` for full API client implementation.

## Offline Mode

When the backend is in offline mode:
- Shows "🧠 Offline Demo Mode" banner
- Uses dummy inbox data from JSON files
- Generates suggestions via local Ollama
- Simulates send actions (no actual emails)

## Components

### Sidebar
Navigation sidebar with inbox, tasks, drafts, and settings links.

### InboxList
Displays message threads with filtering (all, leads, tasks).

### ThreadView
Shows conversation thread with message bubbles and suggestion panel.

### SuggestionPanel
AI suggestion interface with:
- Tone selector (Formal/Warm/Crisp)
- Editable textarea
- Send/Save Draft/Discard buttons
- Prompt & Sources collapsible section

### CommandPalette
Modal command palette with:
- Summarize thread
- Send follow-up
- Show tasks

### ContextPanel
Right-side panel showing:
- Contact information
- Tags and tone preference
- Pending tasks
- AI personality insights

## Styling & Theme

### Matte White Theme

The frontend uses a **Matte White** visual theme inspired by premium personal assistant tools (Superhuman/Linear aesthetic):

- **Background**: Matte white (#F8FAFC) with subtle gradient
- **Glass Cards**: Frosted glass effect with backdrop blur, rounded corners (16px), subtle borders
- **Typography**: Inter font family (Google Fonts)
- **Primary Color**: Electric blue (#0ea5ff) for CTAs and accents
- **Accent Color**: Emerald green (#10b981) for secondary actions
- **Micro-animations**: AI thinking dots with electric blue glow, trailing line animations
- **Design Tokens**: CSS variables defined in `styles/globals.css`

### Glass Card Utility

Use the `GlassCard` component for consistent glass styling:

```tsx
import GlassCard from '@/components/GlassCard';

<GlassCard className="p-6">
  {/* Content */}
</GlassCard>
```

### Toggle Simulated Mode

The header displays a "Simulated Mode" chip when the backend is in offline mode. This is automatically detected via the `/api/health/local` endpoint.

### CSS Variables

- `--bg`: Base background color
- `--card-bg`: Glass card background (rgba white)
- `--glass-border`: Subtle border color
- `--primary`: Electric blue (#0ea5ff)
- `--accent`: Emerald green (#10b981)
- `--muted`: Muted text color
- `--glass-blur`: Backdrop blur amount (10px)

### Tailwind Config

The theme extends Tailwind with:
- Custom primary/accent color scales
- Glass utilities
- Custom animations (glow-pulse, line-draw)
- Spacing tokens

## Accessibility

- Semantic HTML elements
- ARIA labels and roles
- Keyboard navigation
- Focus management
- Skip navigation link

## Development

### Adding a New Page

1. Create file in `app/[page-name]/page.tsx`
2. Add route to Sidebar navigation
3. Update command palette if needed

### Adding a New Component

1. Create component in `components/`
2. Export from component file
3. Import and use in pages

### API Changes

Update `lib/api.ts` with new endpoints and types.

## Troubleshooting

### Backend Connection Error

Ensure backend is running:
```bash
cd ../backend
npm run dev
```

Or use the demo script:
```bash
./scripts/run_local_demo.sh
```

### Port Already in Use

Change port in `package.json`:
```json
"dev": "next dev -p 3001"
```

### Build Errors

Clear Next.js cache:
```bash
rm -rf .next
yarn build
```

## License

MIT

