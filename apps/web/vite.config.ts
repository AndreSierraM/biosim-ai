import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev-only: same-origin /v1 so browsers never hit API CORS from alt ports.
    proxy: { "/v1": "http://localhost:8123" },
  },
});
