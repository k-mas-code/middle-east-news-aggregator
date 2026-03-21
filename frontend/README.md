# Middle East News Aggregator - Frontend

React + TypeScript frontend for the Middle East News Aggregator.

## ✓ Task 12 Complete

### Task 12.1: Report List (Requirements 5.1, 5.6)
- ✓ Display all reports with topic names and media sources
- ✓ Show system status and last update time
- ✓ Responsive card layout with hover effects

### Task 12.2: Report Detail & Bias Chart (Requirements 5.2, 5.3, 5.4)
- ✓ Detailed report view with full articles
- ✓ Interactive bias comparison chart (Recharts)
- ✓ Original article links for all sources
- ✓ Entity extraction display
- ✓ Media-specific article grouping

### Task 12.3: Search (Requirement 5.5)
- ✓ Keyword search functionality
- ✓ Real-time results display

## Development

```bash
npm install         # Install dependencies
npm run dev         # Run dev server (http://localhost:5173)
npm test            # Run tests
npm run build       # Build for production
```

## Environment Variables

Create `.env.local`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

## Tech Stack

- React 19 + TypeScript
- Vite 8
- React Router v7
- Recharts 3
- Vitest + React Testing Library

## API Client Tests

13 tests implemented (all passing):
- Fetch operations
- Error handling
- URL encoding
- Query parameters
