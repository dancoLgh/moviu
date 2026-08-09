# Hero And Icon Redesign

## Objective

Make the first screen easier to scan and replace improvised symbols and hand-drawn interface SVGs with a coherent icon system.

## Hero

The headline becomes “Tu web imprime local.” with one natural visual break between the proposition and its highlighted local outcome. The supporting text is shortened to one direct explanation of the HTTPS bridge. A wider hero grid and tighter line height prevent the copy column from fragmenting into multiple short lines while retaining the product dashboard as the primary visual proof.

## Icons And Brand

Lucide supplies navigation, action, platform, security, format, checklist, and status icons from a pinned CDN version. HTML uses semantic `data-lucide` placeholders and keeps labels available when the CDN is unavailable. The Moviu logo is not replaced by a generic library icon: the official isotipo is optimized as a local 256-pixel PNG and reused in the header, dashboard preview, download dialog, footer, and favicon.

## Responsive Behavior

Desktop gives the copy enough width to hold the first headline phrase on one line. Below the desktop breakpoint the dashboard moves underneath the copy. Mobile typography scales down so the compact message remains readable, buttons become full width, and Lucide icons retain consistent dimensions.
