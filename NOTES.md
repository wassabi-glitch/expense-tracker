# Teaching preferences

- Financial mathematics must be introduced with small concrete numbers and row-by-row balance changes before showing a general formula.
- Always identify the exact number being multiplied, added, or subtracted; avoid unexplained algebra and finance terminology.
- Relate every mathematical distinction directly to the Payment Plan field, schedule row, or ledger behavior it changes.
- Before comparing two financial concepts, show where each concept sits in the Payment Plan decision tree and state whether it changes the current v1 scope.

# Mobile build preferences

- Build the mobile client and backend in vertical slices: when a mobile screen, details page, or modal exposes a missing backend capability, implement and verify that backend work as part of the same slice.
- Guide the mobile build one immediate step at a time because this is the user's first mobile application.
- The current target is to reach a shippable Sarflog release within 75 days; protect that deadline by separating launch-critical scope from post-launch scope.
- Preserve Sarflog's current primary color as a fixed brand constraint during the mobile redesign; other visual-system decisions may be reconsidered around it.
