import * as esbuild from "esbuild";
import { copyFileSync, mkdirSync, cpSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "src");
const www = join(here, "www");

mkdirSync(www, { recursive: true });

await esbuild.build({
  entryPoints: [join(src, "main.ts")],
  bundle: true,
  format: "esm",
  outfile: join(www, "bundle.js"),
  platform: "browser",
  target: "es2022",
});

copyFileSync(join(src, "index.html"), join(www, "index.html"));
copyFileSync(join(src, "styles.css"), join(www, "styles.css"));

console.log("Built → www/");
