import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import fs from 'fs';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  base: '/static/',
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          src: 'node_modules/monaco-editor/min/vs',
          dest: ''
        }
      ]
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'src': path.resolve(__dirname, './src'),
    }
  },
  optimizeDeps: {
    exclude: ['lucide-react'],
    include: ['monaco-editor/esm/vs/editor/editor.worker']
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          jsonWorker: ['monaco-editor/esm/vs/language/json/json.worker'],
          cssWorker: ['monaco-editor/esm/vs/language/css/css.worker'],
          htmlWorker: ['monaco-editor/esm/vs/language/html/html.worker'],
          tsWorker: ['monaco-editor/esm/vs/language/typescript/ts.worker'],
          editorWorker: ['monaco-editor/esm/vs/editor/editor.worker'],
        },
      },
    },
    sourcemap: false
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
});
