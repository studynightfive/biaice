import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "标策 AI",
    short_name: "标策 AI",
    description: "本地自托管、可追溯的投标决策辅助工作区。",
    start_url: "/projects",
    display: "standalone",
    background_color: "#f1eee6",
    theme_color: "#1d2b26",
    lang: "zh-CN",
  };
}
