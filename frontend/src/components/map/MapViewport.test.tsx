import '@testing-library/jest-dom'
import React from 'react'
import { render, screen } from '@testing-library/react'
import { useSimulationStore } from '@/store/simulationStore'

// Mock deck.gl and maplibre-gl since they rely on WebGL/canvas
jest.mock('@deck.gl/react', () => {
  const DeckGLMock = React.forwardRef(function DeckGLMock(props: any, ref: any) {
    return React.createElement('div', { 'data-testid': 'deckgl' }, props.children)
  })
  return { __esModule: true, default: DeckGLMock }
})

jest.mock('react-map-gl/maplibre', () => {
  function MapMock(props: any) {
    return React.createElement('div', { 'data-testid': 'maplibre-map' }, props.children)
  }
  function NavControlMock() {
    return React.createElement('div', { 'data-testid': 'nav-control' })
  }
  return { __esModule: true, default: MapMock, NavigationControl: NavControlMock }
})

jest.mock('@deck.gl/core', () => ({
  MapView: class MapViewMock {
    constructor(public opts: any) {}
  },
}))

jest.mock('@deck.gl/layers', () => ({
  GeoJsonLayer: class GeoJsonLayerMock {
    constructor(public opts: any) {}
  },
}))

jest.mock('@deck.gl/geo-layers', () => ({
  H3HexagonLayer: class H3HexagonLayerMock {
    constructor(public opts: any) {}
  },
}))

jest.mock('@deck.gl/aggregation-layers', () => ({
  HeatmapLayer: class HeatmapLayerMock {
    constructor(public opts: any) {}
  },
}))

jest.mock('h3-js', () => ({
  cellToLatLng: jest.fn(() => [17.385, 78.4867]),
}))

jest.mock('./MapLegend', () => ({
  MapLegend: () => React.createElement('div', { 'data-testid': 'map-legend' }, 'MapLegend'),
}))

jest.mock('./MapControlsHUD', () => ({
  MapControlsHUD: () => React.createElement('div', { 'data-testid': 'map-controls-hud' }, 'MapControlsHUD'),
}))

// Must import component after mocks
const { MapViewport } = require('./MapViewport')

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('MapViewport', () => {
  it('renders without crashing', () => {
    render(React.createElement(MapViewport))

    expect(screen.getByTestId('deckgl')).toBeInTheDocument()
    expect(screen.getByTestId('maplibre-map')).toBeInTheDocument()
    expect(screen.getByTestId('nav-control')).toBeInTheDocument()
  })

  it('shows loading state when no frames (no legend, no frame info)', () => {
    render(React.createElement(MapViewport))

    // No frames => no MapLegend, no month counter
    expect(screen.queryByTestId('map-legend')).not.toBeInTheDocument()
    expect(screen.queryByText(/Month/)).not.toBeInTheDocument()
    // HUD controls are always visible
    expect(screen.getByTestId('map-controls-hud')).toBeInTheDocument()
  })

  it('handles empty regionBoundary gracefully', () => {
    useSimulationStore.setState({
      regionBoundary: null,
    })

    // Should not throw
    const { container } = render(React.createElement(MapViewport))
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders MapLegend when frames are present', () => {
    useSimulationStore.setState({
      activeFrameIndex: 0,
      frames: [
        {
          month: 1,
          timestamp: '2024-01-01',
          cells: [],
          metrics: {
            gdpDelta: 0,
            unemploymentRate: 0,
            realEstateIndex: 0,
            transitCongestion: 0,
            informalEmployment: 0,
            housingAffordability: 0,
            floodDisruption: 0,
            migrationBalance: 0,
          },
          activeLoop: 'primary',
          proof: {
            formula: 'test',
            dataQuality: 'good',
            cellCount: 0,
            activeEffects: [],
          },
        } as any,
      ],
    })

    render(React.createElement(MapViewport))

    expect(screen.getByTestId('map-legend')).toBeInTheDocument()
    expect(screen.getByText(/Month 1/)).toBeInTheDocument()
  })

  it('shows correct month info with parsed scenario horizon', () => {
    useSimulationStore.setState({
      parsedScenario: { horizon_months: 24 } as any,
      activeFrameIndex: 0,
      frames: [
        {
          month: 3,
          timestamp: '2024-03-01',
          cells: [],
          metrics: {
            gdpDelta: 0,
            unemploymentRate: 0,
            realEstateIndex: 0,
            transitCongestion: 0,
            informalEmployment: 0,
            housingAffordability: 0,
            floodDisruption: 0,
            migrationBalance: 0,
          },
          activeLoop: 'primary',
          proof: {
            formula: 'test',
            dataQuality: 'good',
            cellCount: 0,
            activeEffects: [],
          },
        } as any,
      ],
    })

    render(React.createElement(MapViewport))

    expect(screen.getByText(/Month 3 \/ 24/)).toBeInTheDocument()
  })

  it('handles regionBoundary with valid GeoJSON', () => {
    const mockBoundary: GeoJSON.Polygon = {
      type: 'Polygon',
      coordinates: [[[78.4, 17.3], [78.5, 17.3], [78.5, 17.4], [78.4, 17.4], [78.4, 17.3]]],
    }

    useSimulationStore.setState({
      regionBoundary: mockBoundary,
    })

    const { container } = render(React.createElement(MapViewport))
    expect(container.firstChild).toBeInTheDocument()
  })
})
