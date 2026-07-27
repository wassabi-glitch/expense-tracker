# Auth Round 3 UI/UX Decisions

This document tracks the elite UI/UX standard decisions made during the planning of the Password Recovery (Round 3) feature across the Web and Mobile platforms.

## 1. Web Frontend Architecture
* **React Hook Form + Zod Integration:** The current web screens (`ForgotPassword.jsx` and `ResetPassword.jsx`) use manual `useState` tracking for their forms. They will be refactored to use `react-hook-form` and `@hookform/resolvers/zod` to match the `Signup.jsx` and `Login.jsx` architecture. This ensures identical validation logic (e.g., password rules) and prevents boilerplate bloat.

## 2. "Forgot Password" Flow
* **Success State (In-Page Replacement):** When a user successfully requests a link, the email input form completely disappears. It is replaced in-page by a large Green Checkmark icon and a message.
* **Enumeration Resistance (The "Ghost User"):** The success state is *always* triggered even if the email does not exist in the database. The message specifically says *"If an account exists, an email was sent..."* to prevent malicious actors from guessing registered emails.
* **Button Hierarchy:** Because the user's primary action is to leave the app and check their email, the "Back to Sign In" button on the success state will be styled as a **secondary** button.
* **Fail States (Inline Only):** There is no global, full-screen fail state for Forgot Password. Errors like rate-limiting (429) or network drops are shown as inline red text or banners on the form itself. This prevents the user from hitting a UX dead-end where an action button (like "Try Again") would just trigger another rate limit.

## 3. "Reset Password" Flow
* **Single Password Input:** The backend schema only requires `new_password`. Following modern UX standards (Nielsen Norman Group), we will only render **one** password input field to reduce friction.
* **Visibility Toggle:** Because we are dropping the "Confirm Password" field, the single password input **must** include a "Show/Hide Password" (eye icon) toggle so users can check for typos.
* **Success State (Closure & Redirection):** Changing a password causes user anxiety. To provide closure, upon a successful backend response, the form will be replaced in-page by a Success checkmark icon and a message. It will wait 2-3 seconds before automatically redirecting to the Sign In screen.
* **Button Hierarchy:** The action button on the success state will be a **primary** "Continue to Sign In" button to confidently lead the user back into the app.
* **Global Fail State (Terminal Errors):** If the backend returns `auth.reset_token_invalid_or_expired` (due to a 30-minute timeout, a double-click on an old link, or a truncated URL), the screen will enter a global Fail State. It will display a massive red `AlertCircle` icon, explain that the link is dead, and provide a "Request New Link" button to safely restart the flow.
