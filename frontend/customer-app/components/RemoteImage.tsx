import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { Image, View } from "react-native";

type RemoteImageProps = {
  uri: string | null | undefined;
  size?: number;
  /** Fill the parent width with this aspect ratio instead of a fixed square. */
  aspectRatio?: number;
  icon?: ComponentProps<typeof Ionicons>["name"];
  rounded?: string;
};

export function RemoteImage({
  uri,
  size = 64,
  aspectRatio,
  icon = "image-outline",
  rounded = "rounded-xl",
}: RemoteImageProps) {
  const sizeStyle = aspectRatio
    ? { width: "100%" as const, aspectRatio }
    : { width: size, height: size };

  if (!uri) {
    return (
      <View
        style={sizeStyle}
        className={`items-center justify-center bg-border ${rounded}`}
      >
        <Ionicons name={icon} size={aspectRatio ? 40 : size / 2.5} color="#7DA0CA" />
      </View>
    );
  }
  return (
    <Image
      source={{ uri }}
      style={sizeStyle}
      resizeMode="cover"
      className={`bg-border ${rounded}`}
    />
  );
}
