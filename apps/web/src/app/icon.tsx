import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const size = { width: 64, height: 64 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 16,
          background: "#315c4d",
          color: "#fffdf7",
          fontFamily: "SimSun, serif",
          fontSize: 38,
          fontWeight: 700,
        }}
      >
        标
      </div>
    ),
    size,
  );
}
