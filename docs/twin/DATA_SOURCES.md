# India Twin data sources

Sources feeding the M1 backbone. Registry ids refer to `backend/app/data_registry.py`.
Place the manual downloads as described in `data/twin/manual/README.md`.

## Local Government Directory
- Registry id: `lgd`
- URL: https://lgdirectory.gov.in/
- Licence: Government Open Data License - India
- Feeds: the place hierarchy (states and current districts, LGD codes, Census 2011 codes) in `places.parquet`.

## Survey of India administrative boundaries
- Registry id: `soi-boundaries`
- URL: https://onlinemaps.surveyofindia.gov.in/
- Licence: Survey of India terms
- Feeds: district boundaries and the India outline; state and country layers are dissolved from the districts. These are the only boundaries drawn.

## Census 2011 Primary Census Abstract (district)
- Registry id: `census2011-pca-district`
- URL: https://censusindia.gov.in/
- Licence: Government Open Data License where marked
- Feeds: population, sex split, literacy and worker indicators, apportioned from 2011 districts onto current districts via the crosswalk.

## Census 2011 district boundaries (DataMeet)
- Registry id: `census2011-district-boundaries`
- URL: https://github.com/datameet/maps
- Licence: CC BY 2.5 IN
- Feeds: the 2011 to current district crosswalk only. These boundaries are used only for the crosswalk and are never drawn.

## VIIRS Nighttime Lights
- Registry id: `viirs`
- URL: https://eogdata.mines.edu/products/vnl/
- Licence: Public-domain US Government data
- Feeds: the `nightlights_radiance_sum` indicator, a per-district zonal sum of annual average-masked radiance. A proxy for economic activity, not GDP.
