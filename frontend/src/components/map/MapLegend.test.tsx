import '@testing-library/jest-dom'
import { act, render, screen } from '@testing-library/react'
import { MapLegend } from './MapLegend'
import { useSimulationStore } from '@/store/simulationStore'
import type { MapMetricKey } from '@/lib/colorScale'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('MapLegend', () => {
  it('renders legend with color stops for delta metric', () => {
    useSimulationStore.setState({ activeMetric: 'delta' as MapMetricKey })

    const { container } = render(<MapLegend />)

    // Should render the label
    expect(screen.getByText(/Economic Impact/)).toBeInTheDocument()

    // Should render color stop boxes (5 stops for delta)
    const colorBoxes = container.querySelectorAll('.w-4.h-4.rounded-sm')
    expect(colorBoxes.length).toBe(5)
  })

  it('shows correct metric label for delta', () => {
    useSimulationStore.setState({ activeMetric: 'delta' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Economic Impact (Δ GDP)')).toBeInTheDocument()
  })

  it('shows correct label for job density metric', () => {
    useSimulationStore.setState({ activeMetric: 'jobDensity' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Total Job Density (Viridis)')).toBeInTheDocument()
  })

  it('shows correct label for congestion metric', () => {
    useSimulationStore.setState({ activeMetric: 'congestion' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Transit Congestion (Magma)')).toBeInTheDocument()
  })

  it('shows correct label for real estate metric', () => {
    useSimulationStore.setState({ activeMetric: 'realEstateIndex' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Real Estate Index')).toBeInTheDocument()
  })

  it('shows correct label for flood risk metric', () => {
    useSimulationStore.setState({ activeMetric: 'floodRisk' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Flood Risk Index')).toBeInTheDocument()
  })

  it('shows correct label for air quality metric', () => {
    useSimulationStore.setState({ activeMetric: 'airQuality' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Air Quality Index')).toBeInTheDocument()
  })

  it('shows correct label for water stress metric', () => {
    useSimulationStore.setState({ activeMetric: 'waterStress' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('Water Stress Index')).toBeInTheDocument()
  })

  it('formats delta stop labels with percentage', () => {
    useSimulationStore.setState({ activeMetric: 'delta' as MapMetricKey })

    render(<MapLegend />)

    // Delta stops: -25%, -8%, 0%, +8%, +25%
    expect(screen.getByText('-25%')).toBeInTheDocument()
    expect(screen.getByText('+25%')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('formats congestion stop labels with percentage', () => {
    useSimulationStore.setState({ activeMetric: 'congestion' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('formats job density stop labels with k suffix', () => {
    useSimulationStore.setState({ activeMetric: 'jobDensity' as MapMetricKey })

    render(<MapLegend />)

    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('3.8k')).toBeInTheDocument()
    expect(screen.getByText('7.5k')).toBeInTheDocument()
    expect(screen.getByText('15.0k')).toBeInTheDocument()
  })

  it('renders color boxes with correct background colors', () => {
    useSimulationStore.setState({ activeMetric: 'delta' as MapMetricKey })

    const { container } = render(<MapLegend />)

    const colorBoxes = container.querySelectorAll('.w-4.h-4.rounded-sm')
    const firstBox = colorBoxes[0] as HTMLElement
    expect(firstBox.style.backgroundColor).toBe('rgb(239, 68, 68)')
  })

  it('changes stops when metric changes', () => {
    useSimulationStore.setState({ activeMetric: 'delta' as MapMetricKey })

    const { container, rerender } = render(<MapLegend />)
    const deltaBoxes = container.querySelectorAll('.w-4.h-4.rounded-sm')
    expect(deltaBoxes.length).toBe(5)

    act(() => {
      useSimulationStore.setState({ activeMetric: 'floodRisk' as MapMetricKey })
    })
    rerender(<MapLegend />)
    const floodBoxes = container.querySelectorAll('.w-4.h-4.rounded-sm')
    expect(floodBoxes.length).toBe(3)
  })
})
