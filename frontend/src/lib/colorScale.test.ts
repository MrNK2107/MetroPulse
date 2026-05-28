import { metricToRGBA, heatmapWeight, formatDelta, getLegendStops } from './colorScale'

describe('colorScale', () => {
  describe('metricToRGBA', () => {
    it('returns valid RGBA array for delta metric', () => {
      const result = metricToRGBA(0.05, 'delta')
      expect(result).toHaveLength(4)
      result.forEach((v) => {
        expect(v).toBeGreaterThanOrEqual(0)
        expect(v).toBeLessThanOrEqual(255)
      })
    })

    it('returns valid RGBA for jobDensity metric', () => {
      const result = metricToRGBA(100, 'jobDensity')
      expect(result).toHaveLength(4)
    })

    it('returns valid RGBA for congestion metric', () => {
      const result = metricToRGBA(0.5, 'congestion')
      expect(result).toHaveLength(4)
    })

    it('returns valid RGBA for realEstateIndex metric', () => {
      const result = metricToRGBA(1.5, 'realEstateIndex')
      expect(result).toHaveLength(4)
    })

    it('returns valid RGBA for floodRisk metric', () => {
      const result = metricToRGBA(0.8, 'floodRisk')
      expect(result).toHaveLength(4)
    })
  })

  describe('heatmapWeight', () => {
    it('clamps NaN to 0', () => {
      const result = heatmapWeight(NaN, 'delta')
      expect(result).toBeGreaterThanOrEqual(0)
      expect(result).toBeLessThanOrEqual(100)
    })

    it('returns 50 for midpoint of delta (0.0)', () => {
      const weight = heatmapWeight(0.0, 'delta')
      expect(weight).toBeCloseTo(50, 0)
    })

    it('returns 0 for minimum clamp value', () => {
      const weight = heatmapWeight(-0.15, 'delta')
      expect(weight).toBeCloseTo(0, 0)
    })

    it('returns 100 for maximum clamp value', () => {
      const weight = heatmapWeight(0.15, 'delta')
      expect(weight).toBeCloseTo(100, 0)
    })
  })

  describe('formatDelta', () => {
    it('formats positive with + sign', () => {
      expect(formatDelta(0.052)).toBe('+5.2%')
    })

    it('formats negative with - sign', () => {
      expect(formatDelta(-0.031)).toBe('-3.1%')
    })

    it('formats zero without sign', () => {
      expect(formatDelta(0)).toBe('+0.0%')
    })
  })

  describe('getLegendStops', () => {
    it('returns correct number of stops', () => {
      const stops = getLegendStops('delta')
      expect(stops).toHaveLength(5)
    })

    it('returns stops with value and color', () => {
      const stops = getLegendStops('delta')
      stops.forEach((stop) => {
        expect(stop).toHaveProperty('value')
        expect(stop).toHaveProperty('color')
        expect(stop.color).toMatch(/^rgb\(/)
      })
    })
  })
})
