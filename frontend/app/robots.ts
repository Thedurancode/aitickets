import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || "https://ai-tickets.fly.dev";

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/checkout", "/success", "/tickets", "/events/*/admin"],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
