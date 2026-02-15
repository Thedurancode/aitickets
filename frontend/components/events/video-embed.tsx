"use client";

interface VideoEmbedProps {
  url: string;
  title?: string;
}

function getYouTubeId(url: string): string | null {
  const patterns = [
    /youtube\.com\/watch\?v=([^&]+)/,
    /youtu\.be\/([^?]+)/,
    /youtube\.com\/embed\/([^?]+)/,
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

export function VideoEmbed({ url, title = "Video" }: VideoEmbedProps) {
  const youtubeId = getYouTubeId(url);

  if (youtubeId) {
    return (
      <div className="relative aspect-video rounded-xl overflow-hidden border border-white/5">
        <iframe
          src={`https://www.youtube.com/embed/${youtubeId}`}
          title={title}
          className="absolute inset-0 w-full h-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <div className="relative aspect-video rounded-xl overflow-hidden border border-white/5 bg-black">
      <video src={url} controls className="w-full h-full object-contain" />
    </div>
  );
}
