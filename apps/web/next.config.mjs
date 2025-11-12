/** @type {import('next').NextConfig} */
const nextConfig = {
  cacheComponents: true,
  outputFileTracingIncludes: {
    "**/*": ["supabase/**"],
  },
};

export default nextConfig;
