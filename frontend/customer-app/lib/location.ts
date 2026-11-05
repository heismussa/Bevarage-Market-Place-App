import * as Location from "expo-location";
import { useCallback, useEffect, useState } from "react";

export type Coords = { lat: number; lng: number };

export type LocationStatus = "loading" | "granted" | "denied" | "unavailable";

const round = (value: number) => Math.round(value * 1e5) / 1e5;

/** Last successful position, shared between screens so we only prompt once. */
let lastKnown: Coords | null = null;

/** Ask for permission (if needed) and read the current position. */
export async function getCurrentCoords(): Promise<Coords | null> {
  const permission = await Location.requestForegroundPermissionsAsync();
  if (permission.status !== Location.PermissionStatus.GRANTED) {
    return null;
  }
  const position = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.Balanced,
  });
  return {
    lat: round(position.coords.latitude),
    lng: round(position.coords.longitude),
  };
}

export function useUserLocation(): {
  status: LocationStatus;
  coords: Coords | null;
  refresh: () => Promise<void>;
} {
  const [status, setStatus] = useState<LocationStatus>(lastKnown ? "granted" : "loading");
  const [coords, setCoords] = useState<Coords | null>(lastKnown);

  const refresh = useCallback(async () => {
    setStatus("loading");
    try {
      const next = await getCurrentCoords();
      if (next) {
        lastKnown = next;
        setCoords(next);
        setStatus("granted");
      } else {
        setCoords(null);
        setStatus("denied");
      }
    } catch {
      setCoords(null);
      setStatus("unavailable");
    }
  }, []);

  useEffect(() => {
    // Screens opened later reuse the position already read by the home tab.
    if (!lastKnown) void refresh();
  }, [refresh]);

  return { status, coords, refresh };
}
