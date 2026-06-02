import '@testing-library/jest-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { PresetSelector } from './PresetSelector'
import { useSimulationStore } from '@/store/simulationStore'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

describe('PresetSelector', () => {
  it('starts collapsed and shows toggle button', () => {
    render(<PresetSelector />)

    expect(screen.getByText('Quick Presets')).toBeInTheDocument()
    // Preset buttons should not be visible initially
    expect(screen.queryByText('Tech Boom')).not.toBeInTheDocument()
  })

  it('expands to show all 6 preset buttons when clicked', () => {
    render(<PresetSelector />)

    fireEvent.click(screen.getByText('Quick Presets'))

    const presetNames = [
      'Tech Boom',
      'Manufacturing Push',
      'Real Estate Crisis',
      'Infrastructure Focus',
      'Pharma SEZ',
      'Balanced Growth',
    ]
    presetNames.forEach((name) => {
      expect(screen.getByText(name)).toBeInTheDocument()
    })
  })

  it('presets contain Indian city names in descriptions', () => {
    render(<PresetSelector />)
    fireEvent.click(screen.getByText('Quick Presets'))

    expect(screen.getByText(/Bengaluru/)).toBeInTheDocument()
    expect(screen.getByText(/Chennai/)).toBeInTheDocument()
    expect(screen.getByText(/Mumbai/)).toBeInTheDocument()
    expect(screen.getByText(/Delhi NCR/)).toBeInTheDocument()
    expect(screen.getByText(/Hyderabad/)).toBeInTheDocument()
    expect(screen.getByText(/Pune/)).toBeInTheDocument()
  })

  it('clicking a preset sets the scenario text and collapses', () => {
    render(<PresetSelector />)
    fireEvent.click(screen.getByText('Quick Presets'))

    fireEvent.click(screen.getByText('Tech Boom'))

    const store = useSimulationStore.getState()
    expect(store.scenarioText).toBe(
      'Bengaluru IT sector grows 30% with Digital India policy investment for 24 months'
    )
    // Should collapse after selection
    expect(screen.queryByText('Tech Boom')).not.toBeInTheDocument()
  })

  it('clicking a preset calls flyToCity with the correct city', () => {
    const flyToCity = jest.spyOn(
      useSimulationStore.getState(),
      'flyToCity'
    )

    render(<PresetSelector />)
    fireEvent.click(screen.getByText('Quick Presets'))
    fireEvent.click(screen.getByText('Manufacturing Push'))

    expect(flyToCity).toHaveBeenCalledWith('chennai')

    flyToCity.mockRestore()
  })

  it('can toggle open and closed', () => {
    render(<PresetSelector />)

    // Open
    fireEvent.click(screen.getByText('Quick Presets'))
    expect(screen.getByText('Tech Boom')).toBeInTheDocument()

    // Close
    fireEvent.click(screen.getByText('Quick Presets'))
    expect(screen.queryByText('Tech Boom')).not.toBeInTheDocument()
  })

  it('each preset has a description line', () => {
    render(<PresetSelector />)
    fireEvent.click(screen.getByText('Quick Presets'))

    expect(screen.getByText(/Bengaluru IT\/ITES growth/)).toBeInTheDocument()
    expect(screen.getByText(/Chennai manufacturing expansion/)).toBeInTheDocument()
    expect(screen.getByText(/Mumbai real estate decline/)).toBeInTheDocument()
    expect(screen.getByText(/Delhi NCR transport investment/)).toBeInTheDocument()
    expect(screen.getByText(/Hyderabad pharma SEZ/)).toBeInTheDocument()
    expect(screen.getByText(/Pune multi-sector balanced/)).toBeInTheDocument()
  })
})
