import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { deltaToRGBA } from "@/lib/colorScale";
import type { HexCellState } from "@/types/simulation";

interface HexLayerProps {
  data: HexCellState[];
  resolution?: number;
  extruded?: boolean;
}

export class HexLayer extends H3HexagonLayer<HexCellState> {
  static layerName = "HexLayer";

  constructor(props: HexLayerProps) {
    const { data, resolution = 8, extruded = true } = props;
    super({
      data,
      getHexagon: (d: HexCellState) => d.h3Index,
      getFillColor: (d: HexCellState) => deltaToRGBA(d.delta, d.jobDensity),
      getElevation: (d: HexCellState) => d.jobDensity / 2,
      elevationScale: 10,
      extruded,
      resolution,
      coverage: 0.9,
      filled: true,
      wireframe: false,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 80],
    });
  }
}
