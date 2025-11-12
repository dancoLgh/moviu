/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    ppr: true
  },
  outputFileTracingIncludes: {
    "**/*": ["supabase/**"]
  }
};

export default nextConfig;
