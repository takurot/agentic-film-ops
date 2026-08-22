# Google Cloud Products Used in Agentic FilmOps

## 1. Google Gemini 2.5 Flash via Gemini API
- **Gemini 2.5 Flash**: Structures untrusted manager replies, summarizes vendor responses, and generates producer-facing recommendation explanations. Deterministic Python code performs orchestration and constraint solving.

## 2. Google Gen AI SDK
- Provides direct, asynchronous Gemini model access. The FastAPI backend manages execution lifecycles, parallel dispatch, and validated MCP stdio routing across 6 specialized domain agents (**Weather, Script, Actor, Location, Equipment, and Budget Agents**).

## 3. Firebase Hosting (Google Cloud)
- Serves as the global cloud delivery and deployment platform for the Next.js 16 web application at [https://takurot0708.web.app](https://takurot0708.web.app).
- Configured with global edge CDN distribution, SPA rewrite routing, and optimized Range-request headers for seamless 1080p MP4 promotional video and WebVTT subtitle streaming.

---

### Quick Copy-Paste Summary (for Devpost forms):
- **Google Gemini 2.5 Flash**: Structured reasoning over untrusted talent and vendor communications, plus recommendation explainability.
- **Google Gen AI SDK**: Direct Gemini model access for structured reasoning and explainability. Multi-agent coordination and MCP tool routing are implemented by the FastAPI backend.
- **Firebase Hosting (Google Cloud)**: Global CDN web deployment, single-page application routing, and optimized media streaming at https://takurot0708.web.app.
