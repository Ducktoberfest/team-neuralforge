const esbuild = require("esbuild");

const isProduction = process.argv.includes("--production");

esbuild.build({
  entryPoints: ["src/extension.ts"],
  bundle: true,
  outfile: "dist/extension.js",
  external: ["vscode"],
  format: "cjs",
  platform: "node",
  target: "node18",
  sourcemap: !isProduction,
  minify: isProduction,
  logLevel: "info",
}).catch(() => process.exit(1));
