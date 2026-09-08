import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { transform } from "sucrase";

// ---------------------------------------------------------------------------
// Plugin: compile fe_*.ts as TSX using sucrase (bypasses esbuild .ts limitation)
// ---------------------------------------------------------------------------
function tsxTestFiles() {
  const RE = /\/test\/fe_\d+\.ts$/;
  return {
    name: "tsx-test-files",
    enforce: "pre" as const,
    transform(code: string, id: string) {
      if (!RE.test(id)) return null;
      const result = transform(code, {
        transforms: ["typescript", "jsx"],
        jsxRuntime: "automatic",
        production: false,
      });
      return { code: result.code, map: result.sourceMap };
    },
  };
}

export default defineConfig({
  plugins: [tsxTestFiles(), react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  // Disable esbuild for .ts files that we handle ourselves via sucrase
  esbuild: {
    exclude: [/\/test\/fe_\d+\.ts$/] as unknown as RegExp[],
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
    include: ["test/fe_*.ts", "test/fe_*.tsx"],
  },
});


