import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { deltaToRGBA } from "@/lib/colorScale";
import type { HexCellState } from "@/types/simulation";

interface HexLayerProps {
  data: HexCellState[];
  extruded?: boolean;
}

export class HexLayer extends H3HexagonLayer<HexCellState> {
  static layerName = "HexLayer";

  constructor(props: HexLayerProps) {
    const { data, extruded = true } = props;
    super({
      data,
      getHexagon: (d: HexCellState) => d.h3Index,
      getFillColor: (d: HexCellState) => deltaToRGBA(d.delta, d.jobDensity),
      getElevation: (d: HexCellState) => Math.max(10, (d.jobDensity + d.jobDensityInformal) / 200),
      elevationScale: 18,
      extruded,
      coverage: 0.9,
      filled: true,
      wireframe: false,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 80],
    });
  }
}
