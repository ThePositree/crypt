import { defineConfig } from "oxlint";

export default defineConfig({
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  plugins: ["typescript", "react", "jsx-a11y", "import"],
  settings: {
    next: {
      rootDir: ".",
    },
    react: {
      version: "19.2.1",
    },
  },
});
