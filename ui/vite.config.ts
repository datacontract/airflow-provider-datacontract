import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";

// Dev-only: serve the XCom results endpoint from a fixture so `npm run dev`
// renders the view standalone, without an Airflow instance behind it.
const mockResultsApi = (): Plugin => ({
  name: "mock-datacontract-results-api",
  apply: "serve",
  configureServer(server) {
    server.middlewares.use("/datacontract/api/results", (_req, res) => {
      res.setHeader("Content-Type", "application/json");
      res.end(readFileSync(resolve("dev-fixtures", "results.json"), "utf8"));
    });
  },
});

// Follows the Airflow react-plugin template contract: UMD bundle named
// "AirflowPlugin", React shared with the host application via globals.
export default defineConfig({
  base: "./",
  build: {
    lib: {
      entry: resolve("src", "main.tsx"),
      fileName: "main",
      formats: ["umd"],
      name: "AirflowPlugin",
    },
    outDir: "dist",
    rollupOptions: {
      external: ["react", "react-dom", "react-router-dom", "react/jsx-runtime"],
      output: {
        globals: {
          react: "React",
          "react-dom": "ReactDOM",
          "react-router-dom": "ReactRouterDOM",
          "react/jsx-runtime": "ReactJSXRuntime",
        },
      },
    },
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  plugins: [react(), mockResultsApi()],
});
