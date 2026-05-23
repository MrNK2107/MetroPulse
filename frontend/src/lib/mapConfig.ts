import type { MapViewState } from "@deck.gl/core";

export const INITIAL_VIEW_STATE: MapViewState = {
  longitude: -73.935242,
  latitude: 40.73061,
  zoom: 11,
  pitch: 45,
  bearing: 0,
};

export const MAP_STYLE = "mapbox://styles/mapbox/dark-v11";
export const H3_RESOLUTION = 8;
