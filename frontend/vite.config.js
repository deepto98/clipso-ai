import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// Vite configuration with explicit allowedHosts for Replit
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  define: {
    // Fix for process.env usage in client code
    "process.env": {}
  },
  server: {
    // Listen on all interfaces
    host: "0.0.0.0",
    port: 5000,
    // Simple proxy configuration
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
    // Explicitly allow the Replit domain
    allowedHosts: [
      // The specific Replit domain shown in the error
      "5538f7bb-4937-4c98-a69b-b66c60b15a8a-00-m07esigwe069.janeway.replit.dev",
      // Wildcards for Replit domains
      "*.replit.dev",
      "*.repl.co",
      // Allow all hosts as fallback
      "all"
    ],
  },
});
