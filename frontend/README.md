# Agentic FilmOps frontend

The dashboard has two explicit, fail-closed build profiles:

- `RECORDED_REPLAY`: bundled sample data; no backend, SSE, or WebSocket traffic.
- `LIVE_GEMINI`: requires `NEXT_PUBLIC_API_URL` and verifies the backend runtime handshake before displaying Live data.

```bash
npm ci
cp .env.example .env.local
npm run dev
```

For local Live development, use `NEXT_PUBLIC_FILMOPS_MODE=LIVE_GEMINI` with an
explicit local API URL. Production Live builds require a non-loopback HTTPS
endpoint. The public Firebase deployment must remain `RECORDED_REPLAY` until
Issue #88 adds authentication, exact CORS, rate limiting, and public endpoint
protection.

Verification:

```bash
npm run lint
npx tsc --noEmit
npm test
npm run test:e2e:replay
```
