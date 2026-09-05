import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
// Design decision: path alias "@" -> src/ so imports stay clean
// (e.g. `import { AuthContext } from "@/context/AuthContext"`)
// instead of relative "../../../" chains as the app grows.
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        host: true,
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
