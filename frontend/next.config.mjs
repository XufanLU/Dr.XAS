/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    AWS_ACCESS_KEY_ID: process.env.AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY: process.env.AWS_SECRET_ACCESS_KEY,
    AWS_BUCKET_NAME: process.env.AWS_BUCKET_NAME,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'test-dr-xas.s3.eu-north-1.amazonaws.com',
      },
    ],
  },
};

export default nextConfig;
