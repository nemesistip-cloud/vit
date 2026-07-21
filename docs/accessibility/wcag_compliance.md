# VIT Network — Accessibility & WCAG Compliance Standards

**Version:** 6.0.0
**Domain:** /docs/accessibility/
**Status:** Approved Reference

---

## 1. Compliance Mandate

The VIT Network portal is committed to providing a fully accessible experience to all users, including professional traders, validators, and researchers with visual, auditory, motor, or cognitive disabilities. The interface is engineered to conform to the **W3C Web Content Accessibility Guidelines (WCAG) 2.1 Level AA** standards.

---

## 2. Visual Standards & Color Contrast

- **Minimum Contrast Ratio:** All text and critical UI elements must achieve a contrast ratio of at least **4.5:1** against their background colors. Large text ($\ge 18\text{pt}$ or bold $\ge 14\text{pt}$) must maintain a contrast of at least **3:1**.
- **Non-Color Reliance:** Color must never be used as the *sole* means of conveying information, indicating an action, prompting a response, or distinguishing a visual element. For example, status badges must combine colored indicator dots with explicit text labels ("Healthy", "Degraded").
- **Contrast Checkers:** All primary layout variations are automatically checked using Lighthouse and axe-core accessibility scanners.

---

## 3. Keyboard Navigation & Focus States

A cornerstone of our WCAG AA compliance is **full keyboard operability**. Users must be able to navigate and interact with every element of the platform shell and workspaces using only a keyboard.

### 3.1 Focus Indicators
- **Rule:** A highly visible focus ring must surround any interactive component when focused.
- **Style:** Focused elements must display a custom blue ring (`ring-2 ring-blue-400 ring-offset-2 ring-offset-slate-950`). Standard browser default outlines are suppressed (`outline-none`) only when custom rings are correctly bound.

### 3.2 Focus Trapping in Modals
- When an overlay dialog, drawer, or modal is opened, keyboard focus must be **trapped** inside that modal. Focus must not cycle out into background canvas links.
- Focus trapping is driven by the `<FocusScope>` React primitive from `@radix-ui/react-focus-scope`.
- Pressing `Escape` must instantly dismiss any open overlay and return focus to the trigger button that launched it.

---

## 4. Screen Reader Support & ARIA Attributes

To support assistive technologies such as screen readers (NVDA, JAWS, VoiceOver), elements must be accompanied by appropriate ARIA attributes:

- **Alternative Image Texts:** Every informational icon or image must feature descriptive alternative text (`alt="..."` or `aria-label="..."`). Decorative icons must be hidden from screen readers using `aria-hidden="true"`.
- **Dynamic Content Announcements:** Real-time data streams or status changes (such as a node syncing status transition) must be announced to screen readers using ARIA live regions:
  ```html
  <div aria-live="polite" class="sr-only">Subsystem resource_platform is now healthy.</div>
  ```
- **Semantic HTML:** Avoid generic `<div>` tags for interactive elements. Utilize native `<button>`, `<nav>`, `<aside>`, and `<header>` tags to preserve built-in screen reader navigation anchors.
