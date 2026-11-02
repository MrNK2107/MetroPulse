from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

from engine.config import DATA_DIR, CityConfig


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    name: str
    owner: str
    domains: tuple[str, ...]
    geography: str
    cadence: str
    retrieval_method: str
    license: str
    confidence_class: str
    url: str
    temporal_coverage: str = "varies by release"
    freshness_sla_days: int = 365
    checksum_policy: str = "sha256"
    transform_version: str = "registry-v1"
    observation_time_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["domains"] = list(self.domains)
        return data


SOURCE_REGISTRY: tuple[SourceDefinition, ...] = (
    SourceDefinition("census-pca", "Population Census / Primary Census Abstract", "ORGI", ("population", "employment"), "town/urban agglomeration", "decennial", "download", "Government Open Data License where marked", "measured_official", "https://censusindia.gov.in/"),
    SourceDefinition("mospi-plfs", "Periodic Labour Force Survey", "MoSPI/NSO", ("employment",), "state and urban/rural", "monthly/quarterly/annual", "download", "Government publication", "measured_official", "https://mospi.gov.in/"),
    SourceDefinition("mospi-asi-asuse", "ASI and ASUSE", "MoSPI/NSO", ("economy", "employment"), "state/district where published", "annual", "download", "Government publication", "measured_official", "https://mospi.gov.in/"),
    SourceDefinition("dpiit-fdi", "FDI Factsheets", "DPIIT", ("economy",), "state and sector", "quarterly", "download", "Government publication", "measured_official", "https://dpiit.gov.in/"),
    SourceDefinition("rbi-dbie", "Database on Indian Economy", "RBI", ("economy", "housing"), "national/state/select city", "monthly/quarterly", "download", "RBI terms", "measured_official", "https://dbie.rbi.org.in/"),
    SourceDefinition("nhb-residex", "NHB RESIDEX", "National Housing Bank", ("housing",), "select city", "quarterly", "download", "NHB terms", "measured_official", "https://residex.nhbonline.org.in/"),
    SourceDefinition("bhuvan-thematic", "Bhuvan Thematic Services", "NRSC/ISRO", ("land_use", "climate", "environment"), "national/state/city layers", "dataset release", "WMS/WMTS/download", "Bhuvan terms by layer", "measured_official", "https://bhuvan.nrsc.gov.in/"),
    SourceDefinition("imd-rainfall", "IMD Rainfall and Weather", "India Meteorological Department", ("climate",), "grid/district/subdivision", "daily", "download/feed", "IMD terms", "measured_official", "https://mausam.imd.gov.in/"),
    SourceDefinition("vahan", "VAHAN Public Dashboard", "MoRTH/NIC", ("mobility",), "state/RTO", "daily/monthly", "dashboard/export", "Government portal terms", "measured_official", "https://analytics.parivahan.gov.in/"),
    SourceDefinition("smart-cities", "Smart Cities Open Data", "MoHUA", ("mobility", "environment", "services"), "city", "varies", "API/download", "Government Open Data License - India", "measured_official", "https://smartcities.data.gov.in/"),
    SourceDefinition("cpcb", "National Air Quality Monitoring Programme", "CPCB", ("environment",), "station/city", "hourly/daily", "API/download", "Government portal terms", "measured_official", "https://cpcb.nic.in/", freshness_sla_days=7),
    SourceDefinition("municipal-catalogs", "Municipal budgets and open-data catalogs", "Urban local bodies", ("economy", "services"), "city", "annual/varies", "allow-listed download", "Source-specific", "licensed_secondary", "https://data.gov.in/", freshness_sla_days=550),
    SourceDefinition("rera", "State RERA project aggregates", "State RERA authorities", ("housing",), "state/city/project", "monthly/varies", "allow-listed export", "Source-specific", "licensed_secondary", "https://rera.mohua.gov.in/", freshness_sla_days=120),
    SourceDefinition("transit-gtfs", "Transit GTFS feeds", "Transit agencies", ("mobility",), "city/network", "service-change", "GTFS download", "Agency-specific", "licensed_secondary", "https://transit.land/", freshness_sla_days=45),
    SourceDefinition("openstreetmap", "OpenStreetMap", "OpenStreetMap contributors", ("mobility", "land_use"), "national", "continuous", "PBF/Overpass", "ODbL", "open_proxy", "https://www.openstreetmap.org/"),
    SourceDefinition("viirs", "VIIRS Nighttime Lights", "NOAA/NASA", ("economy", "land_use"), "500m grid", "monthly/annual", "download", "Public-domain US Government data", "open_proxy", "https://eogdata.mines.edu/products/vnl/", freshness_sla_days=120),
    SourceDefinition("ghsl", "Global Human Settlement Layer", "European Commission JRC", ("population", "land_use"), "grid", "multi-year release", "download", "European Commission reuse notice", "open_proxy", "https://human-settlement.emergency.copernicus.eu/"),
    SourceDefinition("worldpop", "WorldPop gridded population", "WorldPop, University of Southampton", ("population",), "grid", "annual", "download/API", "CC BY 4.0 where marked", "open_proxy", "https://www.worldpop.org/", freshness_sla_days=550),
    SourceDefinition("gdelt-news", "GDELT / news context", "GDELT and publishers", ("context",), "city query", "near-real-time", "API/RSS", "Source-specific", "context_only", "https://www.gdeltproject.org/"),
    SourceDefinition("lgd", "Local Government Directory", "MoPR / NIC", ("administrative",), "state/district", "continuous", "download", "Government Open Data License - India", "measured_official", "https://lgdirectory.gov.in/"),
    SourceDefinition("soi-boundaries", "Survey of India administrative boundaries", "Survey of India", ("administrative",), "district/state/national", "release", "download", "Survey of India terms", "measured_official", "https://onlinemaps.surveyofindia.gov.in/"),
    SourceDefinition("census2011-pca-district", "Census 2011 Primary Census Abstract (district)", "ORGI", ("population", "employment"), "district (2011 boundaries)", "decennial", "download", "Government Open Data License where marked", "measured_official", "https://censusindia.gov.in/"),
    SourceDefinition("census2011-district-boundaries", "Census 2011 district boundaries (DataMeet; crosswalk only, never drawn)", "DataMeet", ("administrative",), "district (2011 boundaries)", "static", "download", "CC BY 2.5 IN", "open_proxy", "https://github.com/datameet/maps"),
)


# Census million-plus UAs/cities plus state and UT capitals. Entries without a
# checked-in YAML remain visible as limited coverage rather than receiving
# invented baselines.
NATIONAL_CITY_REGISTRY: dict[str, tuple[str, str, float, float, str]] = {
    "agra": ("Agra", "Uttar Pradesh", 27.1767, 78.0081, "million_plus"),
    "ahmedabad": ("Ahmedabad", "Gujarat", 23.0225, 72.5714, "million_plus"),
    "aizawl": ("Aizawl", "Mizoram", 23.7271, 92.7176, "capital"),
    "amritsar": ("Amritsar", "Punjab", 31.6340, 74.8723, "million_plus"),
    "asansol": ("Asansol", "West Bengal", 23.6739, 86.9524, "million_plus"),
    "aurangabad": ("Chhatrapati Sambhajinagar", "Maharashtra", 19.8762, 75.3433, "million_plus"),
    "bengaluru": ("Bengaluru", "Karnataka", 12.9716, 77.5946, "million_plus_capital"),
    "bhopal": ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126, "million_plus_capital"),
    "bhubaneswar": ("Bhubaneswar", "Odisha", 20.2961, 85.8245, "capital"),
    "chandigarh": ("Chandigarh", "Chandigarh", 30.7333, 76.7794, "million_plus_capital"),
    "chennai": ("Chennai", "Tamil Nadu", 13.0827, 80.2707, "million_plus_capital"),
    "coimbatore": ("Coimbatore", "Tamil Nadu", 11.0168, 76.9558, "million_plus"),
    "dehradun": ("Dehradun", "Uttarakhand", 30.3165, 78.0322, "capital"),
    "delhi_ncr": ("Delhi NCR", "Delhi", 28.6139, 77.2090, "million_plus_capital"),
    "dhanbad": ("Dhanbad", "Jharkhand", 23.7957, 86.4304, "million_plus"),
    "durg_bhilai": ("Durg-Bhilai", "Chhattisgarh", 21.1904, 81.2849, "million_plus"),
    "faridabad": ("Faridabad", "Haryana", 28.4089, 77.3178, "million_plus"),
    "gangtok": ("Gangtok", "Sikkim", 27.3389, 88.6065, "capital"),
    "gandhinagar": ("Gandhinagar", "Gujarat", 23.2156, 72.6369, "capital"),
    "ghaziabad": ("Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538, "million_plus"),
    "gwalior": ("Gwalior", "Madhya Pradesh", 26.2183, 78.1828, "million_plus"),
    "guwahati": ("Guwahati/Dispur", "Assam", 26.1445, 91.7362, "million_plus_capital"),
    "hyderabad": ("Hyderabad", "Telangana", 17.3850, 78.4867, "million_plus_capital"),
    "imphal": ("Imphal", "Manipur", 24.8170, 93.9368, "capital"),
    "indore": ("Indore", "Madhya Pradesh", 22.7196, 75.8577, "million_plus"),
    "itanagar": ("Itanagar", "Arunachal Pradesh", 27.0844, 93.6053, "capital"),
    "jabalpur": ("Jabalpur", "Madhya Pradesh", 23.1815, 79.9864, "million_plus"),
    "jaipur": ("Jaipur", "Rajasthan", 26.9124, 75.7873, "million_plus_capital"),
    "jammu": ("Jammu", "Jammu and Kashmir", 32.7266, 74.8570, "capital"),
    "jamshedpur": ("Jamshedpur", "Jharkhand", 22.8046, 86.2029, "million_plus"),
    "jodhpur": ("Jodhpur", "Rajasthan", 26.2389, 73.0243, "million_plus"),
    "kanpur": ("Kanpur", "Uttar Pradesh", 26.4499, 80.3319, "million_plus"),
    "kavaratti": ("Kavaratti", "Lakshadweep", 10.5667, 72.6417, "capital"),
    "kochi": ("Kochi", "Kerala", 9.9312, 76.2673, "million_plus"),
    "kohima": ("Kohima", "Nagaland", 25.6751, 94.1086, "capital"),
    "kolkata": ("Kolkata", "West Bengal", 22.5726, 88.3639, "million_plus_capital"),
    "kollam": ("Kollam", "Kerala", 8.8932, 76.6141, "million_plus"),
    "kota": ("Kota", "Rajasthan", 25.2138, 75.8648, "million_plus"),
    "kozhikode": ("Kozhikode", "Kerala", 11.2588, 75.7804, "million_plus"),
    "leh": ("Leh", "Ladakh", 34.1526, 77.5771, "capital"),
    "lucknow": ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462, "million_plus_capital"),
    "ludhiana": ("Ludhiana", "Punjab", 30.9010, 75.8573, "million_plus"),
    "madurai": ("Madurai", "Tamil Nadu", 9.9252, 78.1198, "million_plus"),
    "malappuram": ("Malappuram", "Kerala", 11.0510, 76.0711, "million_plus"),
    "meerut": ("Meerut", "Uttar Pradesh", 28.9845, 77.7064, "million_plus"),
    "mumbai": ("Mumbai", "Maharashtra", 19.0760, 72.8777, "million_plus_capital"),
    "nagpur": ("Nagpur", "Maharashtra", 21.1458, 79.0882, "million_plus"),
    "nashik": ("Nashik", "Maharashtra", 19.9975, 73.7898, "million_plus"),
    "panaji": ("Panaji", "Goa", 15.4909, 73.8278, "capital"),
    "patna": ("Patna", "Bihar", 25.5941, 85.1376, "million_plus_capital"),
    "port_blair": ("Port Blair", "Andaman and Nicobar Islands", 11.6234, 92.7265, "capital"),
    "prayagraj": ("Prayagraj", "Uttar Pradesh", 25.4358, 81.8463, "million_plus"),
    "puducherry": ("Puducherry", "Puducherry", 11.9416, 79.8083, "capital"),
    "pune": ("Pune", "Maharashtra", 18.5204, 73.8567, "million_plus"),
    "raipur": ("Raipur", "Chhattisgarh", 21.2514, 81.6296, "million_plus_capital"),
    "rajkot": ("Rajkot", "Gujarat", 22.3039, 70.8022, "million_plus"),
    "ranchi": ("Ranchi", "Jharkhand", 23.3441, 85.3096, "million_plus_capital"),
    "shimla": ("Shimla", "Himachal Pradesh", 31.1048, 77.1734, "capital"),
    "shillong": ("Shillong", "Meghalaya", 25.5788, 91.8933, "capital"),
    "srinagar": ("Srinagar", "Jammu and Kashmir", 34.0837, 74.7973, "million_plus_capital"),
    "surat": ("Surat", "Gujarat", 21.1702, 72.8311, "million_plus"),
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366, "million_plus_capital"),
    "thrissur": ("Thrissur", "Kerala", 10.5276, 76.2144, "million_plus"),
    "tiruchirappalli": ("Tiruchirappalli", "Tamil Nadu", 10.7905, 78.7047, "million_plus"),
    "vadodara": ("Vadodara", "Gujarat", 22.3072, 73.1812, "million_plus"),
    "varanasi": ("Varanasi", "Uttar Pradesh", 25.3176, 82.9739, "million_plus"),
    "vasai_virar": ("Vasai-Virar", "Maharashtra", 19.3919, 72.8397, "million_plus"),
    "vijayawada": ("Vijayawada/Amaravati", "Andhra Pradesh", 16.5062, 80.6480, "million_plus_capital"),
    "visakhapatnam": ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185, "million_plus"),
}


DOMAIN_WEIGHTS = {
    "population": 0.20,
    "economy": 0.20,
    "land_use": 0.15,
    "mobility": 0.15,
    "housing": 0.10,
    "climate": 0.10,
    "environment": 0.10,
}


def list_national_cities() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for city_id, (name, state, lat, lng, classification) in NATIONAL_CITY_REGISTRY.items():
        config_path = os.path.join(DATA_DIR, "cities", f"{city_id}.yaml")
        ready = os.path.exists(config_path)
        record: dict[str, Any] = {
            "id": city_id,
            "name": name,
            "state": state,
            "country": "India",
            "center": [lat, lng],
            "zoom": 11,
            "classification": classification,
            "simulationReady": ready,
            "coverageScore": 0.68 if ready else 0.30,
            "coverageLabel": "standard" if ready else "limited",
        }
        if ready:
            cfg = CityConfig.load(city_id)
            record.update(
                population=cfg.population,
                city_type=cfg.city_type,
                center=cfg.center,
                zoom=cfg.zoom,
            )
        else:
            record.update(population=None, city_type="unprofiled")
        result.append(record)
    return sorted(result, key=lambda item: item["name"])


def city_dataset_manifest(city_id: str) -> dict[str, Any] | None:
    if city_id not in NATIONAL_CITY_REGISTRY:
        return None
    ready = os.path.exists(os.path.join(DATA_DIR, "cities", f"{city_id}.yaml"))
    domain_scores = {
        "population": 0.75 if ready else 0.45,
        "economy": 0.55 if ready else 0.25,
        "land_use": 0.45 if ready else 0.20,
        "mobility": 0.60 if ready else 0.25,
        "housing": 0.55 if ready else 0.20,
        "climate": 0.55 if ready else 0.35,
        "environment": 0.45 if ready else 0.20,
    }
    score = sum(domain_scores[key] * weight for key, weight in DOMAIN_WEIGHTS.items())
    return {
        "cityId": city_id,
        "coverageScore": round(score, 3),
        "coverageLabel": "high" if score >= 0.80 else "standard" if score >= 0.55 else "limited",
        "domains": domain_scores,
        "fallbackOrder": ["city", "district", "state", "national", "synthetic"],
        "sources": [source.to_dict() for source in SOURCE_REGISTRY],
        "gaps": [] if ready else ["city_config", "validated_boundary", "city_baselines"],
    }
