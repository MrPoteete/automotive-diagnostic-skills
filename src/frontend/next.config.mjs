/** @type {import('next').NextConfig} */
const nextConfig = {
    transpilePackages: ['@carbon/react', '@carbon/icons-react'],
    typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
