# Download And Donation Modal Design

## Objective

Give users clear feedback after choosing a Moviu binary while offering an optional way to support the project through dLocal Go.

## Experience

Windows and Linux download links open an accessible modal. A three-second countdown starts immediately and triggers the original GitHub release download regardless of donation activity. Closing the modal does not cancel the pending download. A direct-download link remains available for browser failures or repeated downloads.

## Donations

The modal offers the four provided USD amounts: 5, 10, 20, and 100. USD 10 is selected by default. The official dLocal Go script is loaded once, and each checkout is initialized only when its amount is selected. The client-side checkout identifier supplied by dLocal Go is used exclusively with the hosted SDK; no private API credentials or server calls are added to GitHub Pages.

## Resilience And Accessibility

SDK loading failures display a non-blocking message and never interrupt the binary download. The dialog exposes native ARIA semantics, moves focus to its close button, supports Escape, restores the previous focus, and adapts to narrow mobile screens.
