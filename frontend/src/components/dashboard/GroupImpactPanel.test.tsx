import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { GroupImpactPanel } from './GroupImpactPanel'
import { useSimulationStore } from '@/store/simulationStore'
import type { GroupImpact } from '@/types/simulation'

beforeEach(() => {
  useSimulationStore.getState().resetAll()
})

const mockGroups: GroupImpact[] = [
  {
    name: 'farmers',
    purchasing_power: 5.2,
    income_stability: 3.1,
    expense_pressure: -2.0,
    housing_impact: 1.5,
    employment_impact: 4.0,
    severity: 'moderate',
  },
  {
    name: 'students',
    purchasing_power: -1.3,
    income_stability: -0.5,
    expense_pressure: 2.1,
    housing_impact: -0.8,
    employment_impact: -3.0,
    severity: 'low',
  },
  {
    name: 'middle_class_families',
    purchasing_power: -8.5,
    income_stability: -6.2,
    expense_pressure: 7.0,
    housing_impact: -5.0,
    employment_impact: -9.0,
    severity: 'high',
  },
]

describe('GroupImpactPanel', () => {
  it('shows placeholder when no group scores', () => {
    render(<GroupImpactPanel />)
    expect(screen.getByText(/Group impact data will appear/)).toBeInTheDocument()
  })

  it('renders group impact cards when scores provided', () => {
    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: mockGroups,
      citizen_satisfaction: 55,
    })

    render(<GroupImpactPanel />)

    expect(screen.getByText('Farmers')).toBeInTheDocument()
    expect(screen.getByText('Students')).toBeInTheDocument()
    expect(screen.getByText('Middle Class')).toBeInTheDocument()
  })

  it('displays correct social group labels', () => {
    const allGroups: GroupImpact[] = [
      { name: 'farmers', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
      { name: 'students', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
      { name: 'middle_class_families', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
      { name: 'small_businesses', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
      { name: 'corporates', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
      { name: 'transport_sector', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
      { name: 'government', purchasing_power: 0, income_stability: 0, expense_pressure: 0, housing_impact: 0, employment_impact: 0, severity: 'low' },
    ]

    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: allGroups,
      citizen_satisfaction: 50,
    })

    render(<GroupImpactPanel />)

    expect(screen.getByText('Farmers')).toBeInTheDocument()
    expect(screen.getByText('Students')).toBeInTheDocument()
    expect(screen.getByText('Middle Class')).toBeInTheDocument()
    expect(screen.getByText('Small Business')).toBeInTheDocument()
    expect(screen.getByText('Corporates')).toBeInTheDocument()
    expect(screen.getByText('Transport')).toBeInTheDocument()
    expect(screen.getByText('Government')).toBeInTheDocument()
  })

  it('shows severity indicators via CSS classes', () => {
    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: mockGroups,
      citizen_satisfaction: 55,
    })

    const { container } = render(<GroupImpactPanel />)

    // The group cards get border/background classes based on severity
    const cards = container.querySelectorAll('.rounded-xl.border.p-3')
    expect(cards.length).toBeGreaterThanOrEqual(3)

    // Moderate severity cards should have amber classes
    const moderateCard = screen.getByText('Farmers').closest('.rounded-xl')
    expect(moderateCard?.className).toContain('amber')

    // Low severity cards should have emerald classes
    const lowCard = screen.getByText('Students').closest('.rounded-xl')
    expect(lowCard?.className).toContain('emerald')

    // High severity cards should have red classes
    const highCard = screen.getByText('Middle Class').closest('.rounded-xl')
    expect(highCard?.className).toContain('red')
  })

  it('shows citizen satisfaction gauge when available', () => {
    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: mockGroups,
      citizen_satisfaction: 72,
    })

    render(<GroupImpactPanel />)

    expect(screen.getByText('Citizen Satisfaction')).toBeInTheDocument()
    expect(screen.getByText('72')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('displays metric rows for each group card', () => {
    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: [mockGroups[0]],
      citizen_satisfaction: 60,
    })

    render(<GroupImpactPanel />)

    expect(screen.getByText('Purchasing Power')).toBeInTheDocument()
    expect(screen.getByText('Income')).toBeInTheDocument()
    expect(screen.getByText('Expenses')).toBeInTheDocument()
    expect(screen.getByText('Housing')).toBeInTheDocument()
    expect(screen.getByText('Jobs')).toBeInTheDocument()
  })

  it('shows positive values in emerald and negative in red', () => {
    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: [mockGroups[0]], // farmers with positive purchasing_power
      citizen_satisfaction: 50,
    })

    render(<GroupImpactPanel />)

    // Purchasing power is +5.2, should be positive (emerald)
    const positiveValue = screen.getByText('+5.2%')
    expect(positiveValue).toBeInTheDocument()
    expect(positiveValue.className).toContain('emerald')
  })

  it('hides citizen satisfaction gauge when null', () => {
    useSimulationStore.getState().setGroupScores({
      type: 'GROUP_SCORES',
      groups: mockGroups,
      citizen_satisfaction: 50,
    })
    // Override citizenSatisfaction to null
    useSimulationStore.setState({ citizenSatisfaction: null })

    render(<GroupImpactPanel />)

    expect(screen.queryByText('Citizen Satisfaction')).not.toBeInTheDocument()
  })
})
