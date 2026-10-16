## What I found
- **App framework:** Vite + React 19 + TypeScript
- **Package manager:** npm
- **Agent framework:** @assistant-ui/react (^0.15.26)
- **Model provider:** Local runtime simulator / Gemini Live WebSocket loop
- **Where components live:** web/src/components/assistant-ui

## What I will install
- `@/components/assistant-ui/elements/thinking-indicator.tsx` (Official pulsing beacon, shimmer label, and elapsed badge)
- `@/components/assistant-ui/elements/shimmer-label.tsx` (Official fade-in shimmer label primitive)
- `@/components/assistant-ui/elements/surfaces.tsx` (Official elapsed time badge token)
- `@/components/assistant-ui/thinking.tsx` (Runtime integration consuming useAuiState and useElapsedLabel)

## Steps
1. Verify assistant-ui packages and directory structure
2. Install official ThinkingIndicator, ShimmerLabel, and SurfaceBadge element components
3. Create runtime AssistantThinking component consuming useAuiState and live elapsed timer
4. Wire AssistantThinking into thread.tsx AssistantMessage component
5. Verify build and runtime with npm run build
