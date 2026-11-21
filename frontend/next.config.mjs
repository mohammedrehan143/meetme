/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "https://meetme-8r0u.onrender.com";
    const cleanUrl = backendUrl.replace(/\/api\/?$/, "");
    return [
      {
        source: '/api/:path*',
        destination: `${cleanUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
