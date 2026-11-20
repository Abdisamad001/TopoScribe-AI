import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Local Packet Tracer proxy (/api/pt/*) needs a Next.js server — static
  // `output: 'export'` cannot host server routes or hold PACKETTRACER_TOKEN.
  images: { unoptimized: true },
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
