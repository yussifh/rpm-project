import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

// Design decision: path alias "@" -> src/ so imports stay clean
// (e.g. `import { AuthContext } from "@/context/AuthContext"`)
// instead of relative "../../../" chains as the app grows.
export default defineConfig({
  plugins: [
    react(),
    // PWA support: the app can be "installed" on a phone/desktop and its
    // shell (HTML/JS/CSS/icons) loads offline. Design decision: ONLY the
    // static app shell is precached — vitals/health API responses are the
    // opposite of "cache offline", so Workbox uses no runtime caching for
    // them; when the device reconnects the app refreshes live data as
    // normal. Workbox's default runtime-cache for navigation fallback
    // stays enabled which is exactly the SPA-served-offline behavior.
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["apple-touch-icon.png", "pwa-192x192.png", "pwa-512x512.png"],
      manifest: {
        name: "RPM System — Remote Patient Monitoring",
        short_name: "RPM System",
        description:
          "AI-integrated remote patient monitoring for diabetes, hypertension, and stroke — predicts risk from your vitals and explains it.",
        theme_color: "#22A996",
        background_color: "#FFFFFF",
        display: "standalone",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        navigateFallback: "/index.html",
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: true,
    open: true,
    strictPort: true,
    allowedHosts: true,
  },
  preview: {
    // The app is served through ephemeral trycloudflare.com quick-tunnel
    // URLs (phone demo of the PWA); those hosts must be permitted or Vite
    // answers "Blocked request" for every asset.
    allowedHosts: [".trycloudflare.com", "localhost"],
  },
  build: {
    rollupOptions: {
      output: {
        // Split the heavy vendor libs into their own chunks so no single
        // file exceeds Vite's 500 kB warning threshold and the app shell
        // loads independently of the chart/UI libs.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          recharts: ["recharts"],
          charts: ["chart.js", "react-chartjs-2"],
        },
      },
    },
  },
});
