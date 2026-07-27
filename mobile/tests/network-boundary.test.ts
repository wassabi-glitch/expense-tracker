import axios from 'axios';
import { HttpResponse, http } from 'msw';

import { server } from './mocks/server';

test('intercepts an API request without contacting a real backend', async () => {
  server.use(
    http.get('https://api.sarflog.test/health', () =>
      HttpResponse.json({ status: 'ok' }),
    ),
  );

  const response = await axios.get<{ status: string }>(
    'https://api.sarflog.test/health',
  );

  expect(response.data).toEqual({ status: 'ok' });
});
