import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

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
  plugins: [react()],
});
