/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    cacheComponents: true
  },
  outputFileTracingIncludes: {
    "**/*": ["supabase/**"]
  }
};

export default nextConfig;
