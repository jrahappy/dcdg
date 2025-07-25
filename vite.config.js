import { defineConfig } from "vite";
import { resolve } from "path";
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
    // Vite configuration options
    base: "/static/",
    build: {
        manifest: "manifest.json",
        outDir: resolve("./assets"),
        rollupOptions: {
            input: {
                test: resolve("./static/js/main.js")
            }
        }
    },
    plugins: [
        tailwindcss()
    ]
})
