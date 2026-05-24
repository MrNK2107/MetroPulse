import type { MapViewState } from "@deck.gl/core";

export const INITIAL_VIEW_STATE: MapViewState = {
  longitude: 78.4867,
  latitude: 17.385,
  zoom: 10,
  pitch: 45,
  bearing: 0,
};

export const MAP_STYLE =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export const H3_RESOLUTION = 8;
