import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

/**
 * Shared HTTP boundary for Jest tests. Individual tests own their handlers so
 * a handler cannot silently leak behavior into an unrelated test suite.
 */
export const handlers = [
  http.get('*/health', () => {
    return HttpResponse.json({ status: 'ok' });
  }),
  http.post('*/sign-up', async ({ request }) => {
    const data = await request.json() as any;
    if (data.email === 'conflict@test.com') {
      return HttpResponse.json({ detail: 'auth.email_already_registered' }, { status: 400 });
    }
    if (data.username === 'conflict') {
      return HttpResponse.json({ detail: 'auth.username_already_taken' }, { status: 400 });
    }
    if (data.email === 'ratelimit@test.com') {
      return HttpResponse.json({ detail: 'auth.signup_rate_limited' }, { status: 429 });
    }
    return HttpResponse.json(
      {
        user: { id: 'user-1', email: data.email, username: data.username },
        access_token: 'fake-token',
        token_type: 'bearer',
        verification_email_sent: data.email !== 'fail-delivery@test.com',
      },
      { status: 201 }
    );
  }),
  http.post('*/resend-verification', async ({ request }) => {
    const data = await request.json() as any;
    if (data.email === 'error@test.com') {
      return HttpResponse.json({ detail: 'Some error' }, { status: 500 });
    }
    return HttpResponse.json({ success: true }, { status: 200 });
  }),
];

export const server = setupServer(...handlers);
