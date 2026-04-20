# UI Usability Guide for Session Shell

## Operator Flow Requirements

The session shell must answer these four questions immediately without guidance:

### 1. **What is happening right now?**
- Clear scene description visible above the fold
- Current situation established clearly
- Character state/mood apparent

### 2. **What changed this turn?**
- Recent state deltas highlighted
- Visible indication of effect from operator input
- Changes listed in plain language

### 3. **What can I do?**
- Input form always findable without scrolling
- Clear prompt: "What happens next?"
- Submit button labeled "Execute Turn"

### 4. **Where is diagnostic help?**
- Debug panel available but not intrusive
- Collapsed by default, expandable on demand
- Only shown to users who need deep diagnostics

---

## Visual Hierarchy

| Priority | Component | Purpose |
|----------|-----------|---------|
| **Primary** | Scene Panel | Story, narrative, current situation |
| **Secondary** | Interaction Panel | Operator input form, execute button |
| **Tertiary** | History Panel | Past turns, context for reference |
| **Diagnostic** | Debug Panel | Deep inspection, diagnostic data |

### Layout Principles

- **Header**: Session metadata (module, turn counter, status, scene)
- **Main content**: Single column, top-to-bottom flow
- **Scene panel**: Largest, most prominent
- **Interaction panel**: Medium size, always visible without scrolling
- **History panel**: Scrollable if needed, below interaction
- **Debug panel**: Collapsed details element, expandable

---

## Clarity Rules

1. **Section headers visible and descriptive**
   - H2 for major sections (Scene, Interaction, History, Debug)
   - Clear purpose for each section

2. **Current turn always visible at top**
   - Session header shows turn counter
   - Turn metadata updated after each execution

3. **Input form never requires scrolling to find**
   - Interaction panel in viewport (mobile-friendly)
   - Submit button immediately adjacent to textarea

4. **Debug panel collapsed by default**
   - Expandable via `<details>` element
   - Doesn't distract from primary flow
   - Shows diagnostic info only when requested

5. **State changes highlighted**
   - "What Changed This Turn" subheading
   - Deltas listed in readable format
   - Visual cues (contrast, spacing) for emphasis

6. **No placeholder text in production**
   - Scene content loads from narrative engine
   - History builds from session history
   - Debug data available when expanded

---

## Example Walkthrough

### User opens session shell

```
Session Header:
  "God of Carnage - Turn 5"
  "Status: ACTIVE | Scene: Phase 2 - Pressure"

Scene Panel:
  "The tension in the room is palpable. [Scene narrative...]"

  What Changed This Turn:
  - Annette's emotional state increased to 75
  - Coalition shifted: Michel and Alain align

Interaction Panel:
  "What happens next?"
  [Textarea for input]
  [Execute Turn button]

History Panel:
  (Scrollable list of previous turns)

Debug Panel:
  [Collapsed - click to expand]
```

### User reads without external guidance

1. ✅ "What's happening?" → Scene narrative answers
2. ✅ "What changed?" → Subheading + deltas listed
3. ✅ "How do I act?" → Input form + button
4. ✅ "Where's help?" → Debug panel available if needed

---

## Responsive Design Notes

- **Desktop**: Full-width layout, all panels visible
- **Tablet**: Single column, panels stack vertically
- **Mobile**: Textarea wider, history/debug collapsible

## CSS Classes Used

- `.session-header` — Top navigation, metadata
- `.session-main` — Grid container for panels
- `.panel` — Standard panel styling
- `.scene-panel` — Scene narrative container
- `.scene-changes` — "What Changed This Turn" subheading
- `.interaction-panel` — Operator input form
- `.interaction-form` — Form layout
- `.history-panel` — Turn history scrollable list
- `.debug-panel` — Collapsible debug section

## Testing Checklist

- [ ] Non-developer can see scene without technical jargon
- [ ] Input form visible without scrolling
- [ ] State changes are understandable (not just raw JSON)
- [ ] Debug panel doesn't interfere with normal flow
- [ ] All 4 questions answered from visual inspection alone
