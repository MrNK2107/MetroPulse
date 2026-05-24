import type { MapViewState } from "@deck.gl/core";

export const INITIAL_VIEW_STATE: MapViewState = {
  longitude: -73.935242,
  latitude: 40.73061,
  zoom: 11,
  pitch: 45,
  bearing: 0,
};

export const MAP_STYLE =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export const H3_RESOLUTION = 8;
