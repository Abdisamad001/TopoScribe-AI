import type { NextConfig } from "next";
import path from "path";

// Static export only for Cloudflare Pages (`npm run build`).
// Local `npm run dev` must NOT use export — /api/pt/* Launch PT proxy needs a real Next server.
const staticExport = process.env.NEXT_OUTPUT_EXPORT === "1";

const nextConfig: NextConfig = {
  ...(staticExport ? { output: "export" as const } : {}),
  images: { unoptimized: true },
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
