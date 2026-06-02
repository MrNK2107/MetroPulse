from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4, uuid5

from app.realtime import build_demo_manifest, snapshot_quality
from app.realtime_models import SnapshotData, SnapshotQuality, SourceStatus
from engine.config import CityConfig, list_available_cities
from engine.models import CaseRetrievalAudit, CaseStudy, CaseStudyMatchContext, CityProfile, ParsedScenario

logger = logging.getLogger(__name__)

CASE_STUDY_NAMESPACE = UUID("2d9a2fb0-1442-4d70-a455-03d4f6f9a637")
CASE_STUDY_EMBEDDING_DIMENSIONS = 1536


async def generate_embedding(text: str) -> list[float] | None:
    """Generate an embedding vector for the given text using the configured provider."""
    from app.config import settings

    provider = settings.resolved_embedding_provider.lower()
    model = settings.resolved_embedding_model

    try:
        if provider == "openai" and settings.openai_api_key:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await asyncio.wait_for(
                client.embeddings.create(input=text, model=model),
                timeout=10.0,
            )
            return _valid_embedding(response.data[0].embedding, provider, model)

        if provider == "gemini" and settings.gemini_api_key:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.embed_content,
                    model=model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=CASE_STUDY_EMBEDDING_DIMENSIONS
                    ),
                ),
                timeout=10.0,
            )
            return _valid_embedding(response.embeddings[0].values, provider, model)

        if provider == "ollama":
            import httpx

            base_url = settings.ollama_base_url or "http://localhost:11434"
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    f"{base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return _valid_embedding(resp.json()["embedding"], provider, model)

    except Exception as e:
        logger.warning("Embedding generation failed (%s): %s", provider, e)

    return None


def _case_study_db_id(slug: str) -> str:
    """Map stable app slugs onto the UUID primary key used by Supabase."""
    return str(uuid5(CASE_STUDY_NAMESPACE, slug))


def _valid_embedding(
    embedding: list[float] | tuple[float, ...],
    provider: str,
    model: str,
) -> list[float] | None:
    values = list(embedding)
    if len(values) != CASE_STUDY_EMBEDDING_DIMENSIONS:
        logger.warning(
            "Embedding from %s/%s has %d dimensions; expected %d. Skipping vector.",
            provider,
            model,
            len(values),
            CASE_STUDY_EMBEDDING_DIMENSIONS,
        )
        return None
    return values

LOCAL_CASE_STUDIES: list[CaseStudy] = [
    CaseStudy(
        id="bengaluru-it-infra",
        title="Bengaluru IT Boom and Infrastructure Stress",
        city="Bengaluru",
        year=2023,
        description="IT/ITES growth increased employment and land values while worsening congestion and water stress.",
        outcome="Tech growth boosted high-skill jobs but strained mobility and housing affordability.",
        source="Karnataka economic survey and urban mobility reporting",
        tags=["it_ites", "congestion", "housing"],
        sectors=["it_ites", "real_estate"],
        policies=["Digital India"],
    ),
    CaseStudy(
        id="hyderabad-pharma-sez",
        title="Hyderabad Pharma and Genome Valley SEZ Expansion",
        city="Hyderabad",
        year=2022,
        description="Pharma cluster investment around Genome Valley concentrated industrial employment and supplier activity.",
        outcome="SEZ-linked manufacturing growth produced localized employment gains and logistics demand.",
        source="Telangana industry department reports",
        tags=["manufacturing", "sez", "pharma"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["SEZ Notification", "Make in India"],
    ),
    CaseStudy(
        id="delhi-metro-property",
        title="Delhi Metro Expansion and Property Value Effects",
        city="Delhi NCR",
        year=2024,
        description="Metro access improved labor mobility and increased property premiums near stations.",
        outcome="Transit investment raised adjacent land values while redistributing commuting pressure.",
        source="Urban transport academic studies",
        tags=["transport_logistics", "real_estate", "metro"],
        sectors=["transport_logistics", "real_estate"],
        policies=["Smart City Mission"],
    ),
    CaseStudy(
        id="mumbai-mill-land",
        title="Mumbai Mill Land to Real Estate Transformation",
        city="Mumbai",
        year=2018,
        description="Former industrial land shifted toward commercial and high-end real-estate activity.",
        outcome="Manufacturing decline coincided with real-estate appreciation and affordability stress.",
        source="Mumbai planning and housing studies",
        tags=["manufacturing", "real_estate", "housing"],
        sectors=["manufacturing", "real_estate"],
        policies=["RERA Compliance"],
    ),
    CaseStudy(
        id="chennai-port-corridor",
        title="Chennai Port-Led Industrial Corridor Growth",
        city="Chennai",
        year=2023,
        description="Port and auto-sector activity shaped logistics corridors and formal manufacturing employment.",
        outcome="Transport investment amplified manufacturing gains but increased corridor congestion.",
        source="Tamil Nadu industry and port trust reports",
        tags=["manufacturing", "transport_logistics", "port"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="pune-it-corridor",
        title="Pune IT Corridor and Hinjewadi Growth",
        city="Pune",
        year=2023,
        description="IT parks along Hinjewadi and Kharadi corridors drove employment but created east-west mobility imbalance.",
        outcome="IT employment growth concentrated in western suburbs, worsening commute times for eastern residents.",
        source="Pune metropolitan development authority reports",
        tags=["it_ites", "transport", "housing"],
        sectors=["it_ites", "transport_logistics"],
        policies=["Digital India", "Smart City Mission"],
    ),
    CaseStudy(
        id="jaipur-tourism-heritage",
        title="Jaipur Heritage Tourism and Real Estate Pressure",
        city="Jaipur",
        year=2022,
        description="UNESCO World Heritage designation boosted tourism but increased commercial pressure on old city areas.",
        outcome="Tourism growth raised hospitality employment while straining heritage zone infrastructure.",
        source="Rajasthan tourism department reports",
        tags=["trade_hospitality", "real_estate", "heritage"],
        sectors=["trade_hospitality", "real_estate"],
        policies=["Smart City Mission"],
    ),
    CaseStudy(
        id="lucknow-metro-informal",
        title="Lucknow Metro and Informal Economy Displacement",
        city="Lucknow",
        year=2023,
        description="Metro construction displaced street vendors and informal workers from key corridors.",
        outcome="Transit formalization improved mobility but reduced informal livelihood access in transit zones.",
        source="UP urban development studies",
        tags=["transport_logistics", "informal", "displacement"],
        sectors=["transport_logistics", "informal"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="kolkata-port-logistics",
        title="Kolkata Port Modernization and Logistics Corridor",
        city="Kolkata",
        year=2021,
        description="Kolkata Port Trust modernization increased container throughput but added heavy truck traffic to urban areas.",
        outcome="Port efficiency gains were offset by corridor congestion and air quality concerns.",
        source="Kolkata Port Trust annual reports",
        tags=["transport_logistics", "manufacturing", "congestion"],
        sectors=["transport_logistics", "manufacturing"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="ahmedabad-textile-decline",
        title="Ahmedabad Textile Mill Decline and Urban Renewal",
        city="Ahmedabad",
        year=2019,
        description="Decline of textile mills in eastern Ahmedabad led to large-scale land conversion to commercial and residential use.",
        outcome="Mill land redevelopment increased real estate values but displaced working-class communities.",
        source="Gujarat urban development studies",
        tags=["manufacturing", "real_estate", "informal"],
        sectors=["manufacturing", "real_estate"],
        policies=["RERA Compliance"],
    ),
    CaseStudy(
        id="chandigarh-planned-infrastructure",
        title="Chandigarh Planned City Infrastructure Resilience",
        city="Chandigarh",
        year=2024,
        description="Chandigarh's planned sector-grid layout provided better infrastructure resilience but limited affordable housing supply.",
        outcome="Planning advantages in transit and green space coexist with housing affordability challenges for migrants.",
        source="Chandigarh administration planning reports",
        tags=["housing", "transport", "planning"],
        sectors=["real_estate", "public_admin"],
        policies=["AMRUT", "PM Awas Yojana"],
    ),
    CaseStudy(
        id="bhubaneswar-smart-city",
        title="Bhubaneswar Smart City Mission Implementation",
        city="Bhubaneswar",
        year=2023,
        description="Bhubaneswar won India's Smart City Challenge and invested in integrated command center and transit upgrades.",
        outcome="Smart infrastructure improved city services but benefits concentrated in central zones.",
        source="Bhubaneswar Smart City Limited reports",
        tags=["smart_city", "transport", "digital"],
        sectors=["public_admin", "transport_logistics"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="pmay-national-housing",
        title="PM Awas Yojana Affordable Housing Outcomes",
        city="Hyderabad",
        year=2023,
        description="PMAY subsidies increased affordable housing construction in peri-urban areas across Indian cities.",
        outcome="Housing supply increased but locations often lacked transit connectivity and employment access.",
        source="Ministry of Housing and Urban Affairs reports",
        tags=["housing", "affordable", "policy"],
        sectors=["real_estate", "informal"],
        policies=["PM Awas Yojana"],
    ),
    CaseStudy(
        id="amrut-water-sanitation",
        title="AMRUT Water and Sanitation Infrastructure Outcomes",
        city="Chennai",
        year=2022,
        description="AMRUT funded water supply augmentation and sewerage network expansion in 500 cities.",
        outcome="Infrastructure improved but maintenance capacity varied widely across municipal corporations.",
        source="AMRUT annual reports and CAG audits",
        tags=["water", "sanitation", "infrastructure"],
        sectors=["public_admin"],
        policies=["AMRUT"],
    ),
    CaseStudy(
        id="make-in-india-corridors",
        title="Make in India Manufacturing Corridor Development",
        city="Ahmedabad",
        year=2024,
        description="Delhi-Mumbai Industrial Corridor and DMIC nodes attracted manufacturing investment along transport routes.",
        outcome="Corridor manufacturing created formal jobs but increased freight traffic on urban peripheries.",
        source="DMICDC project reports",
        tags=["manufacturing", "corridor", "logistics"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India", "SEZ Notification"],
    ),
    # ── New case studies: Indore ──────────────────────────────────────
    CaseStudy(
        id="indore-cleanest-city",
        title="Indore Cleanest City Transformation (Swachh Bharat)",
        city="Indore",
        year=2023,
        description="Indore topped Swachh Survekshan rankings six consecutive times through door-to-door waste collection, 100% segregation, and waste-to-energy plants. GDP boost ~1.2% from tourism and civic investment; employment grew ~3% in sanitation and municipal services; real estate values rose ~12% in improved wards; congestion unchanged; net migration +2% as civic brand attracted talent.",
        outcome="Sanitation-driven civic brand improved investment attractiveness and quality of life, though operational costs remain high.",
        source="Swachh Survekshan reports and Indore Municipal Corporation data",
        tags=["sanitation", "smart_city", "waste_management", "swachh_bharat"],
        sectors=["public_admin", "trade_hospitality"],
        policies=["Smart City Mission", "Swachh Bharat Mission"],
    ),
    CaseStudy(
        id="indore-smart-city-bus-rapid",
        title="Indore BRTS and Smart City Integrated Mobility",
        city="Indore",
        year=2022,
        description="Indore's iBus BRTS and Smart City integrated command centre improved mass transit coverage across the city corridor. GDP impact ~0.8% from improved worker mobility; employment grew ~1.5% in transport-linked retail; real estate rose ~8% near BRTS corridors; congestion reduced ~10% on BRT routes; inward migration +1.5%.",
        outcome="BRTS corridor catalysed commercial development and reduced peak-hour travel times on the main arterial route.",
        source="Indore Smart City Limited reports and MoHUA data",
        tags=["transport", "smart_city", "brt", "mobility"],
        sectors=["transport_logistics", "real_estate"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    # ── New case studies: Surat ──────────────────────────────────────
    CaseStudy(
        id="surat-diamond-industry",
        title="Surat Diamond Cutting and Polishing Industry Cluster",
        city="Surat",
        year=2023,
        description="Surat processes ~90% of the world's diamonds with a massive cutting and polishing cluster employing over 800,000 workers. Cluster generated ~8% GDP contribution to Gujarat; employment extremely high but largely informal; real estate demand grew ~15% in Varachha and Katargam; congestion severe in diamond district; strong in-migration from Saurashtra and Rajasthan.",
        outcome="Diamond cluster drives Surat's economy but creates extreme dependence on a single sector with informal labour conditions.",
        source="Gems and Jewellery Export Promotion Council and Surat Municipal Corporation reports",
        tags=["diamonds", "manufacturing", "cluster", "informal", "exports"],
        sectors=["manufacturing", "informal"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="surat-textile-revival",
        title="Surat Synthetic Textile and Man-Made Fibre Hub",
        city="Surat",
        year=2022,
        description="Surat's man-made fibre textile cluster processes ~30 million metres of fabric daily, second only to Mumbai historically. Textile trade contributed ~4% of city GDP; employment ~500,000 in weaving, processing, and trading; real estate grew ~10% in textile market zones; congestion heavy in Ring Road market area; migration positive from UP and Bihar.",
        outcome="Textile cluster provides mass employment but faces GST compliance challenges and competition from China.",
        source="Southern Gujarat Chamber of Commerce and Industry reports",
        tags=["textiles", "manufacturing", "cluster", "gst", "trade"],
        sectors=["manufacturing", "trade_hospitality"],
        policies=["Make in India", "GST"],
    ),
    CaseStudy(
        id="surat-urban-resilience-flood",
        title="Surat Urban Resilience and Flood Management Reform",
        city="Surat",
        year=2021,
        description="After devastating 2006 floods, Surat invested heavily in flood management infrastructure, early warning systems, and riverfront development. GDP recovery ~3.5% above pre-flood trend; employment restored within 2 years; real estate rebounded ~20% in flood-affected zones over 5 years; congestion managed through ring roads; out-migration reversed after infrastructure completion.",
        outcome="Flood resilience investment became a model for Indian cities, though climate risks continue to intensify.",
        source="Surat Municipal Corporation flood management reports and NDMA studies",
        tags=["flood_management", "resilience", "infrastructure", "climate"],
        sectors=["public_admin", "real_estate"],
        policies=["AMRUT", "Smart City Mission"],
    ),
    # ── New case studies: Nagpur ──────────────────────────────────────
    CaseStudy(
        id="nagpur-metro-smart-city",
        title="Nagpur Metro and MIHAN SEZ Economic Corridor",
        city="Nagpur",
        year=2023,
        description="Nagpur Metro Phase 1 and MIHAN (Multi-modal International Cargo Hub and Airport at Nagpur) SEZ aimed to transform central India's logistics hub. Metro improved transit access but ridership below projections; MIHAN attracted IT and aviation MRO firms; GDP growth ~1.5% from SEZ activity; employment +2% in logistics and IT; real estate up ~18% near metro corridors; congestion reduced ~5% on metro routes.",
        outcome="Dual infrastructure investment positioned Nagpur as a logistics hub but SEZ occupancy remained below targets.",
        source="Maharashtra Metro Rail Corporation and MIHAN India Limited reports",
        tags=["metro", "sez", "logistics", "smart_city", "aviation"],
        sectors=["transport_logistics", "manufacturing", "it_ites"],
        policies=["Smart City Mission", "Make in India", "SEZ Notification"],
    ),
    CaseStudy(
        id="nagpur-orange-economy-agriculture",
        title="Nagpur Orange Economy and Agri-Processing Growth",
        city="Nagpur",
        year=2022,
        description="Vidarbha region's orange cultivation around Nagpur drives agri-processing and cold chain logistics. Agri-processing parks created ~15,000 direct jobs; GDP contribution ~2% from processed fruit exports; real estate grew ~5% near Mouda industrial area; congestion minimal; seasonal migration pattern from rural Vidarbha.",
        outcome="Agri-processing added value to raw produce but cold chain infrastructure gaps persist, causing 20-30% post-harvest losses.",
        source="Nagpur Agricultural Produce Market Committee and NABARD reports",
        tags=["agriculture", "food_processing", "cold_chain", "exports"],
        sectors=["agriculture", "manufacturing", "transport_logistics"],
        policies=["Make in India"],
    ),
    # ── New case studies: Visakhapatnam ──────────────────────────────
    CaseStudy(
        id="visakhapatnam-steel-port",
        title="Visakhapatnam Steel and Port-Led Industrial Growth",
        city="Visakhapatnam",
        year=2023,
        description="Vizag's integrated steel plant (RINL) and major port drove heavy industry employment and export logistics. Steel sector contributed ~4% of AP GDP; port throughput grew 8% YoY; employment ~120,000 in steel and port-linked industries; real estate grew ~10% in Gajuwaka corridor; congestion on NH-16 freight route severe; in-migration from north coastal Andhra.",
        outcome="Heavy industry anchor provides stable employment but environmental and congestion externalities are growing.",
        source="Rashtriya Ispat Nigam Limited and Visakhapatnam Port Authority reports",
        tags=["steel", "port", "manufacturing", "heavy_industry", "exports"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="visakhapatnam-it-corridor",
        title="Visakhapatnam IT and Startup Ecosystem Development",
        city="Visakhapatnam",
        year=2022,
        description="AP government's push to develop Vizag as an IT destination through incentives, incubation hubs (like T-Hub Vizag), and AP Fibrenet broadband backbone. IT employment grew ~25% in 3 years to ~40,000; GDP contribution ~1.5%; real estate surged ~22% in Madhurawada IT SEZ area; congestion increased on Beach Road corridor; net inward migration of tech workers from Hyderabad and Chennai.",
        outcome="Vizag emerged as a credible tier-2 IT hub but faces talent retention challenges against Hyderabad and Bengaluru.",
        source="Andhra Pradesh IT department and NASSCOM state reports",
        tags=["it_ites", "startup", "tier2_city", "digital"],
        sectors=["it_ites", "real_estate"],
        policies=["Digital India", "Make in India"],
    ),
    CaseStudy(
        id="visakhapatnam-cyclone-resilience",
        title="Visakhapatnam Cyclone Hudhud Recovery and Resilience",
        city="Visakhapatnam",
        year=2015,
        description="Cyclone Hudhud (2014) caused ₹70,000 crore damage in Vizag; post-disaster reconstruction included improved building codes, green belt restoration, and early warning systems. GDP dipped ~5% in 2014 then recovered 7%+ by 2015; employment recovered within 18 months; real estate fell ~15% then rebounded ~25% by 2016; congestion managed through widened roads during reconstruction.",
        outcome="Disaster recovery demonstrated Indian cities' resilience capacity, with Vizag emerging stronger with better infrastructure.",
        source="NDMA post-Hudhud assessment and Visakhapatnam district administration reports",
        tags=["disaster", "cyclone", "resilience", "reconstruction"],
        sectors=["public_admin", "real_estate", "construction"],
        policies=["AMRUT"],
    ),
    # ── New case studies: Kochi ──────────────────────────────────────
    CaseStudy(
        id="kochi-metro-muziris",
        title="Kochi Metro Rail and Integrated Transit Development",
        city="Kochi",
        year=2023,
        description="Kochi Metro achieved the fastest metro construction in India and integrated water transport (Kochi Water Metro) as a first-of-its-kind system. Metro improved connectivity Aluva-Pettah corridor; GDP boost ~1.2% from construction and improved mobility; employment +2% in metro-linked commercial activity; real estate rose ~15% near stations; congestion reduced ~12% on parallel roads.",
        outcome="Kochi Metro's innovative construction pace and water metro integration became a national model for tier-2 transit.",
        source="Kochi Metro Rail Limited and KMRL operational reports",
        tags=["metro", "water_transport", "transit", "smart_city"],
        sectors=["transport_logistics", "real_estate"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="kochi-smart-city-fort-kochi",
        title="Kochi Smart City and Tourism-IT Convergence",
        city="Kochi",
        year=2022,
        description="Kochi Smart City (InfoPark/Cyberpark) combined IT infrastructure with heritage tourism development in Fort Kochi area. IT employment ~30,000 in InfoPark; GDP contribution ~2%; real estate grew ~20% in Kakkanad IT corridor; heritage tourism sustained ~50,000 livelihoods; congestion worsened on Edappally-Aroor corridor.",
        outcome="Dual IT-tourism economy diversified Kochi's traditional spice-trade base but strained urban infrastructure.",
        source="Kerala IT Mission and Kochi Smart City Limited reports",
        tags=["smart_city", "it_ites", "tourism", "heritage"],
        sectors=["it_ites", "trade_hospitality", "real_estate"],
        policies=["Smart City Mission", "Digital India"],
    ),
    # ── New case studies: Coimbatore ──────────────────────────────────
    CaseStudy(
        id="coimbatore-pump-motor-cluster",
        title="Coimbatore Engineering and Pump Manufacturing Cluster",
        city="Coimbatore",
        year=2023,
        description="Coimbatore manufactures ~50% of India's motors and pumps with over 1,500 engineering firms, plus a growing textile machinery sector. Engineering cluster contributed ~6% of Tamil Nadu industrial GDP; employment ~300,000 in manufacturing; real estate grew ~8% in SIDCO industrial areas; congestion moderate; in-migration from western Tamil Nadu districts.",
        outcome="Diversified engineering cluster provides resilient employment base but faces competition from Chinese imports.",
        source="Coimbatore District Industries Centre and CODISSIA reports",
        tags=["engineering", "manufacturing", "cluster", "pumps", "msme"],
        sectors=["manufacturing", "informal"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="coimbatore-wetlands-development",
        title="Coimbatore Wetlands Loss and Urban Sprawl Impact",
        city="Coimbatore",
        year=2021,
        description="Rapid urbanisation of Coimbatore led to degradation of Singanallur and other tanks/wetlands, worsening flood risk and water scarcity. GDP growth ~3% from real estate but ecological cost high; real estate rose ~12% in former wetland zones; employment in construction grew ~5%; congestion increased on Avinashi Road; flood damage ~₹200 crore in 2019.",
        outcome="Unchecked wetland encroachment created recurring flood vulnerability that now constrains further development.",
        source="Tamil Nadu Pollution Control Board and Coimbatore Corporation reports",
        tags=["wetlands", "urban_sprawl", "flooding", "environment"],
        sectors=["real_estate", "public_admin"],
        policies=["AMRUT"],
    ),
    # ── New case studies: Patna ──────────────────────────────────────
    CaseStudy(
        id="patna-ganga-front-development",
        title="Patna Ganga Riverfront and Urban Renewal",
        city="Patna",
        year=2023,
        description="Patna's ₹2,700 crore Ganga Riverfront Development project transformed 6 km of riverbank into recreational and commercial zones. GDP boost ~0.8% from construction and tourism; employment ~8,000 in riverfront services; real estate surged ~25% near Mahendru-Digha stretch; congestion worsened on Ashok Rajpath; in-migration from rural Bihar continues at ~2% annually.",
        outcome="Riverfront improved Patna's civic image but displaced informal fishermen communities and created gentrification pressure.",
        source="Bihar Urban Infrastructure Development Corporation reports",
        tags=["riverfront", "urban_renewal", "infrastructure", "gentrification"],
        sectors=["real_estate", "public_admin", "trade_hospitality"],
        policies=["AMRUT", "Smart City Mission"],
    ),
    CaseStudy(
        id="patna-education-hub",
        title="Patna Education Coaching Hub and Student Economy",
        city="Patna",
        year=2022,
        description="Patna emerged as a major coaching hub for competitive exams (UPSC, banking, railways) with over 500,000 students migrating annually from Bihar and Jharkhand. Student economy estimated at ₹3,000-4,000 crore annually; employment ~100,000 in coaching, hostels, and support services; real estate grew ~15% in Boring Road and Kankarbagh coaching zones; congestion intense in coaching districts.",
        outcome="Education economy provides significant multiplier effects but creates pressure on housing and urban infrastructure.",
        source="Bihar education department and Patna Municipal Corporation assessments",
        tags=["education", "coaching", "student_economy", "migration"],
        sectors=["education", "real_estate", "informal"],
        policies=["National Education Policy"],
    ),
    # ── New case studies: Bhopal ──────────────────────────────────────
    CaseStudy(
        id="bhopal-smart-city-lake-restoration",
        title="Bhopal Smart City Lake Restoration and Green Infrastructure",
        city="Bhopal",
        year=2023,
        description="Bhopal Smart City focused on Upper Lake conservation, BRTS corridor, and digital infrastructure integration. Lake restoration improved water quality and surrounding real estate; GDP growth ~1% from smart infrastructure projects; employment ~5,000 in green infrastructure and digital services; real estate rose ~10% near Upper Lake; congestion reduced ~8% on BRTS corridor.",
        outcome="Lake-centric smart city approach distinguished Bhopal but BRTS ridership remains below capacity.",
        source="Bhopal Smart City Development Corporation Limited reports",
        tags=["smart_city", "lake_restoration", "green_infrastructure", "brt"],
        sectors=["public_admin", "real_estate", "transport_logistics"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="bhopal-gas-tragedy-long-term",
        title="Bhopal Industrial Redevelopment Post Union Carbide Site",
        city="Bhopal",
        year=2020,
        description="Long-term cleanup and redevelopment planning around the 1984 Union Carbide gas tragedy site shaped Bhopal's industrial policy toward safer, lighter industries. Environmental remediation costs ~₹500 crore; industrial employment shifted from chemicals to IT and food processing; real estate in affected wards depressed ~20% vs city average; contamination fears continue to affect migration patterns.",
        outcome="Industrial disaster legacy constrained chemical sector growth but catalysed diversification into cleaner industries.",
        source="Bhopal Gas Tragedy Relief and Rehabilitation Department and NGT orders",
        tags=["industrial_disaster", "remediation", "environmental_justice", "redevelopment"],
        sectors=["manufacturing", "public_admin"],
        policies=["Make in India"],
    ),
    # ── Disaster case studies ──────────────────────────────────────────
    CaseStudy(
        id="chennai-floods-2015",
        title="Chennai Floods 2015 — Urban Disaster and Recovery",
        city="Chennai",
        year=2015,
        description="December 2015 Chennai floods caused ₹1.2 lakh crore damage from unprecedented rainfall and encroachment of waterways. GDP contracted ~3% in Q4 2015; ~1.8 million workers displaced; real estate fell ~20% in flood-affected zones (Velachery, Tambaram); congestion gridlocked during evacuation; out-migration ~200,000 temporarily. Recovery took 2-3 years with improved stormwater drains.",
        outcome="Chennai floods exposed cost of unplanned urbanisation over wetlands and catalysed stormwater infrastructure investment.",
        source="RBI regional report, TN State Disaster Management Authority, and World Bank post-disaster assessment",
        tags=["floods", "disaster", "climate", "resilience", "wetlands"],
        sectors=["real_estate", "public_admin", "manufacturing"],
        policies=["AMRUT", "Smart City Mission"],
    ),
    CaseStudy(
        id="kerala-floods-2018",
        title="Kerala Floods 2018 — Statewide Disaster and Reconstruction",
        city="Kochi",
        year=2018,
        description="Kerala's worst floods in a century (Aug 2018) affected 5.4 million people, caused ₹40,000 crore damage, and shut down Kochi airport for 2 weeks. State GDP dipped ~2.5%; 200,000+ jobs lost in tourism and agriculture; real estate fell ~15% in affected districts; Kochi port logistics disrupted for 3 weeks; reverse migration of ~500,000 workers to home states.",
        outcome="Flood recovery revealed Kerala's fiscal resilience through diaspora crowdfunding but exposed quarrying and hillside development risks.",
        source="Kerala State Disaster Management Authority, RBI, and UNDP post-flood assessment",
        tags=["floods", "disaster", "climate", "tourism", "agriculture", "resilience"],
        sectors=["public_admin", "trade_hospitality", "agriculture"],
        policies=["AMRUT"],
    ),
    CaseStudy(
        id="mumbai-monsoon-disruptions",
        title="Mumbai Annual Monsoon Disruptions and Economic Cost",
        city="Mumbai",
        year=2023,
        description="Mumbai's annual monsoon flooding (especially severe in 2005, 2017, and recurring annually) causes estimated ₹10,000-15,000 crore annual economic loss from disrupted transport, waterlogging, and infrastructure damage. GDP impact ~0.3-0.5% annually from productivity loss; 500,000+ daily-wage workers lose ~5-10 work days per monsoon; real estate prices suppressed ~5% in chronically flood-prone areas (Kurla, Sion); local trains cancelled 3-5 days annually.",
        outcome="Chronic monsoon disruption is Mumbai's largest recurring economic drag, driving ₹30,000 crore coastal road and drain investments.",
        source="BMC monsoon preparedness reports, IMD data, and Indian Institute of Tropical Meteorology studies",
        tags=["monsoon", "floods", "transport_disruption", "climate", "infrastructure"],
        sectors=["transport_logistics", "public_admin", "informal"],
        policies=["AMRUT"],
    ),
    # ── Policy-specific case studies ──────────────────────────────────
    CaseStudy(
        id="upi-digital-payments-revolution",
        title="UPI Digital Payments Transformation of Urban Commerce",
        city="Bengaluru",
        year=2023,
        description="UPI processed 83 billion transactions worth ₹139 lakh crore in FY2023, transforming urban retail, street vending, and micro-enterprise payments. Digital transaction adoption ~95% in metros; informal sector saw 40% UPI adoption, improving financial inclusion; GDP boost estimated ~0.5-1% from reduced transaction friction; ~500,000 jobs created in fintech; reduced cash handling costs for small merchants.",
        outcome="UPI created world's largest real-time payment ecosystem, formalising parts of the informal economy and enabling fintech growth.",
        source="NPCI UPI statistics, RBI Annual Report, and NASSCOM fintech studies",
        tags=["upi", "digital_payments", "fintech", "informal_economy", "financial_inclusion"],
        sectors=["informal", "trade_hospitality", "it_ites"],
        policies=["Digital India", "Jan Dhan Yojana"],
    ),
    CaseStudy(
        id="gst-informal-economy-impact",
        title="GST Impact on Urban Informal Economy and MSMEs",
        city="Surat",
        year=2019,
        description="GST implementation (2017) significantly affected India's informal economy, with MSMEs in textile, diamond, and manufacturing hubs facing compliance costs and supply chain restructuring. Surat textile traders reported 15-20% initial revenue drop; formal sector employment grew ~5% as businesses registered; informal employment dipped ~3%; compliance costs estimated at 1-2% of MSME revenue; real estate demand shifted toward GST-compliant commercial spaces.",
        outcome="GST accelerated formalisation of urban MSMEs but imposed disproportionate compliance burden on micro-enterprises.",
        source="GST Network data, CAIT reports, and RBI bulletin on informal sector",
        tags=["gst", "taxation", "informal_economy", "msme", "formalisation"],
        sectors=["informal", "manufacturing", "trade_hospitality"],
        policies=["GST"],
    ),
    CaseStudy(
        id="smart-city-mission-outcomes",
        title="Smart City Mission — Pan-India Outcomes Assessment (50 Cities)",
        city="Bhubaneswar",
        year=2024,
        description="Smart City Mission completed 5 years with ₹75,000 crore invested across 100 cities in Integrated Command Centres, adaptive traffic management, and area-based development. Average GDP uplift ~0.8-1.2% in mission cities; 200,000+ direct jobs created; real estate appreciated ~12-18% in area-based development zones; congestion reduced ~8-15% in targeted corridors; 50,000+ CCTV cameras installed for safety.",
        outcome="Mission improved urban services in core areas but benefits remained geographically concentrated, with limited citywide spillover.",
        source="MoHUA Smart City Mission dashboard and evaluation by NIUA",
        tags=["smart_city", "urban_infrastructure", "digital", "command_centre"],
        sectors=["public_admin", "transport_logistics", "it_ites"],
        policies=["Smart City Mission"],
    ),
    CaseStudy(
        id="amrut-mission-urban-infrastructure",
        title="AMRUT Mission — Water Supply and Sewerage Outcomes",
        city="Visakhapatnam",
        year=2023,
        description="AMRUT invested ₹77,640 crore across 500 cities in water supply, sewerage, and green space projects (2015-2023). Cities saw 15-25% improvement in water supply coverage; sewerage network expanded ~30% in mission cities; GDP impact ~0.5% from improved public health and productivity; real estate rose ~8-10% in newly serviced areas; employment in construction grew ~4% during peak investment years.",
        outcome="AMRUT addressed critical infrastructure gaps but maintenance and operational capacity remain challenges for municipal corporations.",
        source="MoHUA AMRUT Atal Mission reports and CAG performance audit",
        tags=["amrut", "water_supply", "sewerage", "urban_infrastructure"],
        sectors=["public_admin"],
        policies=["AMRUT"],
    ),
    CaseStudy(
        id="pmay-housing-periurban",
        title="PM Awas Yojana — Peri-Urban Housing Construction Boom",
        city="Nagpur",
        year=2023,
        description="PMAY-Urban sanctioned 1.18 crore houses nationally, driving peri-urban construction activity in tier-2 cities. Nagpur saw 45,000 PMAY units sanctioned; GDP boost ~1.5% from construction multiplier; employment ~25,000 in housing construction and materials; real estate in PMAY zones rose ~8%; many beneficiaries are 15-25 km from city centre, increasing commute times ~30 minutes.",
        outcome="PMAY dramatically increased affordable housing supply but peripheral locations create transport and livelihood accessibility challenges.",
        source="MoHUA PMAY MIS data and Nagpur Municipal Corporation reports",
        tags=["pmay", "affordable_housing", "construction", "periurban"],
        sectors=["real_estate", "construction", "informal"],
        policies=["PM Awas Yojana"],
    ),
    # ── Sector-specific case studies ──────────────────────────────────
    CaseStudy(
        id="hyderabad-genome-valley-pharma",
        title="Hyderabad Genome Valley — India's Pharma Capital Expansion",
        city="Hyderabad",
        year=2024,
        description="Genome Valley and Pharma City in Hyderabad house 200+ pharma and biotech firms producing ~40% of India's pharmaceutical exports. Pharma sector contributed ~₹50,000 crore to Telangana GDP; employment ~200,000 directly in pharma manufacturing and R&D; real estate surged ~30% in Genome Valley and Shamirpet corridor; heavy truck traffic on NH-44; skilled migration from across India and globally.",
        outcome="Hyderabad's pharma cluster achieved global scale but environmental concerns around Pharma City need resolution.",
        source="Telangana Life Sciences and APIIC reports",
        tags=["pharma", "biotech", "manufacturing", "exports", "cluster"],
        sectors=["manufacturing", "it_ites"],
        policies=["Make in India", "SEZ Notification"],
    ),
    CaseStudy(
        id="bengaluru-startup-ecosystem",
        title="Bengaluru Startup and Venture Capital Ecosystem Growth",
        city="Bengaluru",
        year=2023,
        description="Bengaluru hosts ~35% of India's startups with ₹2.5 lakh crore cumulative VC funding (2014-2023), concentrated in fintech, SaaS, and deeptech. Startup employment ~1.5 million directly; GDP contribution estimated ~8-10% from tech ecosystem; real estate in Koramangala-Indiranagar startup belt rose ~35% in 5 years; traffic congestion worsened ~20%; net migration +300,000 tech workers annually.",
        outcome="Bengaluru's startup density created India's Silicon Valley but infrastructure has not scaled proportionally with growth.",
        source="NASSCOM startup report, Karnataka Economic Survey, and CBRE real estate data",
        tags=["startup", "venture_capital", "it_ites", "fintech", "ecosystem"],
        sectors=["it_ites", "real_estate"],
        policies=["Digital India", "Startup India"],
    ),
    CaseStudy(
        id="delhi-ncr-bfsi-hub",
        title="Delhi NCR BFSI and Financial Services Concentration",
        city="Delhi NCR",
        year=2023,
        description="Delhi NCR (Gurugram-Noida) emerged as India's second-largest BFSI hub after Mumbai, with major bank headquarters, insurance companies, and fintech firms. BFSI sector employs ~500,000 in NCR; contributed ~4% of Haryana and UP GDP; real estate in Cyber City and Sector 62 Noida premium ~40% over average; congestion on Delhi-Gurugram expressway critical; skilled migration from across north India.",
        outcome="NCR's BFSI growth created Gurugram-Noida twin financial corridors but exacerbates Delhi's east-west transport imbalance.",
        source="IBA reports, Haryana industry department, and NCR Planning Board data",
        tags=["bfsi", "financial_services", "fintech", "gurugram", "noida"],
        sectors=["bfsi", "it_ites", "real_estate"],
        policies=["Digital India"],
    ),
    CaseStudy(
        id="ahmedabad-sabarmati-riverfront",
        title="Ahmedabad Sabarmati Riverfront and Urban Transformation",
        city="Ahmedabad",
        year=2022,
        description="Sabarmati Riverfront Development transformed 10.4 km of riverbank into a public promenade, parks, and commercial zones over 2005-2022. Tourism and events generated ₹500+ crore annually; real estate along riverfront rose ~40%; employment ~15,000 in riverfront services; displaced ~10,000 informal settlement families; congestion increased on bridges near riverfront entry points.",
        outcome="Riverfront became Ahmedabad's signature urban project but raised concerns about displacement of low-income communities.",
        source="Sabarmati Riverfront Development Corporation Limited reports",
        tags=["riverfront", "urban_renewal", "tourism", "gentrification", "housing"],
        sectors=["real_estate", "trade_hospitality", "public_admin"],
        policies=["Smart City Mission", "AMRUT"],
    ),
    CaseStudy(
        id="pune-automotive-cluster",
        title="Pune-Chakan Automotive Manufacturing Corridor",
        city="Pune",
        year=2023,
        description="Chakan industrial area hosts Volkswagen, Mercedes-Benz, Bajaj, and 300+ auto-component firms along the Pune-Nashik corridor. Automotive sector contributes ~25% of Pune's industrial GDP; employment ~300,000 in auto manufacturing; real estate in Chakan rose ~20% in 5 years; NH-60 congestion severe from heavy vehicle traffic; large-scale migration from Maharashtra, Karnataka, and North India.",
        outcome="Auto corridor established Pune as India's Detroit but created pressure on rural-to-urban fringe infrastructure.",
        source="Maharashtra industry department and ACMA reports",
        tags=["automotive", "manufacturing", "cluster", "corridor"],
        sectors=["manufacturing", "transport_logistics"],
        policies=["Make in India"],
    ),
    CaseStudy(
        id="jaipur-jewellery-gems-sector",
        title="Jaipur Gems and Jewellery Export Cluster",
        city="Jaipur",
        year=2022,
        description="Jaipur is the global centre for coloured gemstone cutting and polishing with ~30,000 units employing 400,000+ workers. Gems sector contributes ~₹25,000 crore to Rajasthan exports; employment largely in informal/semi-formal workshops; real estate in Johari Bazaar and Sitapura SEZ rose ~12%; congestion severe in old city gem trading areas; seasonal migration from eastern Rajasthan.",
        outcome="Gems cluster provides massive employment but faces challenge of formalisation and labour welfare improvements.",
        source="Gems and Jewellery Export Promotion Council and Rajasthan industries department",
        tags=["gems", "jewellery", "exports", "msme", "informal"],
        sectors=["manufacturing", "informal"],
        policies=["Make in India", "SEZ Notification"],
    ),
    CaseStudy(
        id="kolkata-it-sector-salt-lake",
        title="Kolkata IT/ITES Sector Development at Salt Lake Sector V",
        city="Kolkata",
        year=2023,
        description="Kolkata's Salt Lake Sector V and New Town emerged as an IT/ITES hub with TCS, Wipro, Infosys, and 500+ firms, though growth lagged behind peer cities. IT employment ~200,000; contributed ~2% of Bengal GDP; real estate in Sector V/New Town rose ~15% over 5 years; congestion on EM Bypass increased; net IT migration still negative vs Bengaluru/Hyderabad due to lower salary benchmarks.",
        outcome="Kolkata's IT sector grew but the city has not captured India's tech growth share proportionally to its talent base.",
        source="WBHIDCO and NASSCOM East India reports",
        tags=["it_ites", "tech_hub", "salt_lake", "new_town"],
        sectors=["it_ites", "real_estate"],
        policies=["Digital India", "Smart City Mission"],
    ),
    CaseStudy(
        id="lucknow-up-economy-agriculture-reform",
        title="UP Agriculture Mandi Reform and Rural-Urban Linkages",
        city="Lucknow",
        year=2022,
        description="Uttar Pradesh's electronic National Agriculture Market (eNAM) integration and mandi reforms affected agricultural supply chains radiating from Lucknow. eNAM linked 50+ mandis in UP; reduced middleman margins ~5-8%; GDP boost ~0.3% in agricultural trade; employment in mandi logistics ~20,000; real estate near new mandi infrastructure rose ~5%; rural-to-urban migration from eastern UP continued at ~2%.",
        outcome="Mandi digitisation improved price discovery for farmers but adoption remains partial and traditional intermediaries persist.",
        source="UP Agriculture Marketing Board and eNAM portal data",
        tags=["agriculture", "mandi", "digital", "supply_chain", "rural_urban"],
        sectors=["agriculture", "trade_hospitality", "transport_logistics"],
        policies=["Digital India"],
    ),
]


class DatabaseClient:
    """Supabase-backed DB with in-memory fallback when credentials are missing."""

    def __init__(self):
        self._saved: list[dict[str, Any]] = []
        self._snapshots: dict[str, SnapshotData] = {}
        self._client: Any = None
        self.last_case_retrieval = CaseRetrievalAudit()

    async def connect(self):
        from app.config import settings
        if settings.supabase_url and settings.supabase_key:
            try:
                from supabase import create_client
                from supabase.lib.client_options import SyncClientOptions
                import httpx

                # Pre-configure httpx client to avoid deprecated timeout/verify params
                http_client = httpx.Client(timeout=30.0, verify=True)
                options = SyncClientOptions(
                    postgrest_client_timeout=30.0,
                    httpx_client=http_client,
                )
                self._client = create_client(
                    settings.supabase_url,
                    settings.supabase_key,
                    options=options,
                )
                logger.info("Connected to Supabase at %s", settings.supabase_url)
            except Exception as e:
                logger.warning("Failed to connect to Supabase, using in-memory fallback: %s", e)
                self._client = None
        else:
            logger.info("No Supabase credentials configured, using in-memory storage")

    async def close(self):
        self._client = None

    async def list_regions(self) -> list[dict[str, Any]]:
        return list_available_cities()

    async def get_region_profile(self, region_id: str) -> dict[str, Any] | None:
        try:
            cfg = CityConfig.load(region_id)
        except FileNotFoundError:
            return None
        profile = CityProfile(
            id=region_id,
            city=cfg.name,
            state=cfg.state,
            population=cfg.population,
            key_sectors=sorted(cfg.sector_weights, key=cfg.sector_weights.get, reverse=True)[:4],
            gdp_estimate_crores=int(cfg.baselines.get("gdp_estimate_crores", 0)),
            known_challenges=_known_challenges(cfg.city_type),
            special_zones=[zone.get("name", "Zone") for zone in cfg.special_zones],
            sector_weights=cfg.sector_weights,
            spatial_notes=f"{cfg.name} uses estimated H3 baselines from city center distance, sector weights, flood/slum proxies, and configured policy zones.",
            center=cfg.center,
            zoom=cfg.zoom,
            data_quality="estimated",
        )
        return profile.model_dump()

    async def get_region_boundary(self, region_id: str) -> dict[str, Any] | None:
        try:
            cfg = CityConfig.load(region_id)
            return cfg.get_boundary_polygon(city_name=region_id)
        except Exception:
            return None

    async def get_baseline(self, region_id: UUID | str) -> dict[str, Any] | None:
        rid = str(region_id)
        try:
            cfg = CityConfig.load(rid)
        except FileNotFoundError:
            return None
        return {
            "region_id": rid,
            "gdp_index": 1.0,
            "unemployment": cfg.baselines.get("unemployment_rate", 0.05),
            "real_estate_idx": 1.0,
            "transit_load": 0.5,
            "data_quality": "estimated",
        }

    async def list_data_sources(self, city: str = "bengaluru") -> list[dict[str, Any]]:
        snapshot = await self.get_latest_snapshot(city)
        quality = snapshot_quality(snapshot)
        return [source.model_dump(mode="json") for source in quality.source_manifest.values()]

    async def get_latest_snapshot(self, city: str = "bengaluru") -> SnapshotData | None:
        city_key = city.lower().replace(" ", "_")
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("city_snapshots")
                    .select("*")
                    .eq("city", city_key)
                    .order("snapshot_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    return _snapshot_from_row(result.data[0])
            except Exception as e:
                logger.warning("Latest city snapshot lookup failed, using local fallback: %s", e)
        return self._snapshots.get(city_key)

    async def get_snapshot_quality(self, snapshot_id: str, city: str = "bengaluru") -> SnapshotQuality:
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("city_snapshots")
                    .select("*")
                    .eq("id", snapshot_id)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    return snapshot_quality(_snapshot_from_row(result.data[0]))
            except Exception as e:
                logger.warning("Snapshot quality lookup failed, using local fallback: %s", e)
        snapshot = self._snapshots.get(city.lower().replace(" ", "_"))
        if snapshot and snapshot.id == snapshot_id:
            return snapshot_quality(snapshot)
        return snapshot_quality(None)

    async def save_raw_observation(
        self,
        source_id: str,
        city: str,
        payload: dict[str, Any],
        observed_at: datetime | None = None,
        status: str = "ok",
        source_domain: str = "news",
    ) -> None:
        from app.realtime import payload_hash

        resolved_source_id = await self._resolve_data_source_id(source_id, source_domain)

        record = {
            "source_id": resolved_source_id,
            "city": city.lower().replace(" ", "_"),
            "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "payload_hash": payload_hash(payload),
            "status": status,
        }
        if self._client:
            try:
                await asyncio.to_thread(
                    lambda: self._client.table("raw_observations").insert(record).execute()
                )
            except Exception as e:
                logger.warning("Supabase save_raw_observation failed (table may not exist): %s", e)

    async def _resolve_data_source_id(self, source_name_or_id: str, domain: str) -> str:
        if not self._client:
            return source_name_or_id
        try:
            result = await asyncio.to_thread(
                lambda: self._client.table("data_sources")
                .select("id")
                .eq("name", source_name_or_id)
                .eq("domain", domain)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]["id"]

            record = {
                "name": source_name_or_id,
                "domain": domain,
                "auth_type": "none",
                "update_cadence_sec": 86_400,
                "enabled": True,
            }
            created = await asyncio.to_thread(
                lambda: self._client.table("data_sources")
                .insert(record)
                .execute()
            )
            if created.data:
                logger.info("Created data source row for %s/%s", domain, source_name_or_id)
                return created.data[0]["id"]
        except Exception as e:
            logger.warning("Could not resolve data source %s/%s: %s", domain, source_name_or_id, e)
        return source_name_or_id

    async def save_city_snapshot(self, snapshot: SnapshotData) -> None:
        self._snapshots[snapshot.city] = snapshot
        if self._client:
            record = {
                "id": snapshot.id,
                "city": snapshot.city,
                "snapshot_at": snapshot.snapshot_at.isoformat(),
                "h3_cells": snapshot.h3_cells,
                "aggregate_metrics": snapshot.aggregate_metrics,
                "source_manifest": snapshot.manifest_for_json(),
                "quality_score": snapshot.quality_score,
                "status": snapshot.status,
            }
            try:
                await asyncio.to_thread(
                    lambda: self._client.table("city_snapshots").upsert(record).execute()
                )
            except Exception as e:
                logger.warning(
                    "Supabase save_city_snapshot failed (table may not exist), using in-memory only: %s", e
                )

    async def list_simulations(self, page: int = 1, per_page: int = 20) -> list[dict[str, Any]]:
        start = (page - 1) * per_page
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("simulations")
                    .select("id,region_id,params,horizon_months,result_summary,created_at")
                    .order("created_at", desc=True)
                    .range(start, start + per_page - 1)
                    .execute()
                )
                return result.data
            except Exception:
                logger.debug("Supabase list_simulations failed, using in-memory fallback")
        return self._saved[start : start + per_page]

    async def get_simulation(self, simulation_id: UUID) -> dict[str, Any] | None:
        if self._client:
            try:
                result = await asyncio.to_thread(
                    lambda: self._client.table("simulations")
                    .select("*")
                    .eq("id", str(simulation_id))
                    .limit(1)
                    .execute()
                )
                return result.data[0] if result.data else None
            except Exception:
                logger.debug("Supabase get_simulation failed, using in-memory fallback")
        return next((item for item in self._saved if item["id"] == str(simulation_id)), None)

    async def save_simulation(
        self,
        region_id: UUID | None,
        params: dict[str, Any],
        horizon_months: int,
        result_summary: dict[str, Any],
        cell_states: list[dict[str, Any]],
    ) -> str:
        sim_id = str(uuid4())
        record = {
            "id": sim_id,
            "region_id": str(region_id) if region_id else params.get("city"),
            "params": params,
            "horizon_months": horizon_months,
            "result_summary": result_summary,
            "cell_states": cell_states,
        }
        if self._client:
            try:
                await asyncio.to_thread(
                    lambda: self._client.table("simulations").insert(record).execute()
                )
            except Exception as e:
                logger.warning("Supabase save_simulation failed: %s", e)
        else:
            self._saved.append(record)
            # Evict oldest entries to prevent unbounded memory growth
            if len(self._saved) > 1000:
                self._saved = self._saved[-1000:]
        return sim_id

    async def seed_case_studies(self) -> None:
        """Upsert all local case studies to Supabase with embeddings."""
        if not self._client:
            return
        # Skip if already seeded
        try:
            existing = await asyncio.to_thread(
                lambda: self._client.table("case_studies").select("id", count="exact").limit(1).execute()
            )
            if existing.count and existing.count > 0:
                logger.info("case_studies already seeded (%d rows), skipping", existing.count)
                return
        except Exception:
            pass
        logger.info("Seeding case_studies with embeddings...")
        embedding_available = True
        for case in LOCAL_CASE_STUDIES:
            record = {
                "id": _case_study_db_id(case.id),
                "title": case.title,
                "city": case.city,
                "year": case.year,
                "description": case.description,
                "outcome": case.outcome,
                "source": case.source,
                "tags": case.tags,
                "sectors": case.sectors,
                "policies": case.policies,
            }
            # Generate embedding for semantic search
            if embedding_available:
                embed_text = f"{case.title} {case.description} {' '.join(case.tags)} {' '.join(case.sectors)} {' '.join(case.policies)}"
                embedding = await self._generate_embedding(embed_text)
                if embedding:
                    record["embedding"] = embedding
                else:
                    embedding_available = False
                    logger.info("Case study embeddings unavailable; seeding remaining rows without vectors")
            try:
                await asyncio.to_thread(
                    lambda r=record: self._client.table("case_studies").upsert(r).execute()
                )
            except Exception as e:
                logger.warning("Failed to seed case study %s: %s", case.id, e)

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding vector for text using configured provider."""
        return await generate_embedding(text)

    async def search_case_studies(
        self,
        keywords: list[str] | str,
        city: str | None = None,
        sector: str | None = None,
        policy: str | None = None,
        top_k: int = 5,
        context: CaseStudyMatchContext | None = None,
    ) -> list[CaseStudy]:
        context = context or build_case_study_context(
            city=city,
            sectors=[sector] if sector else [],
            policies=[policy] if policy else [],
            keywords=keywords,
        )
        words = {_normal_token(word) for word in context.keywords if _normal_token(word)}

        # Try pgvector semantic search if Supabase is available
        if self._client and words:
            query_text = " ".join(words)
            embedding = await self._generate_embedding(query_text)
            if embedding:
                try:
                    match_count = max(top_k * 4, 20)
                    rpc_args = {
                        "query_embedding": embedding,
                        "match_count": match_count,
                        "filter_city": _city_lookup_value(context.city),
                        "filter_sectors": context.sectors or None,
                        "filter_policies": context.policies or None,
                    }
                    result = await asyncio.to_thread(
                        lambda emb=embedding: self._client.rpc(
                            "match_case_studies",
                            rpc_args,
                        ).execute()
                    )
                    if result.data:
                        studies = []
                        for row in result.data:
                            studies.append(CaseStudy(
                                id=row.get("id", ""),
                                title=row.get("title", ""),
                                city=row.get("city", ""),
                                year=row.get("year", 0),
                                description=row.get("description", ""),
                                outcome=row.get("outcome", ""),
                                source=row.get("source", ""),
                                tags=row.get("tags", []),
                                sectors=row.get("sectors", []),
                                policies=row.get("policies", []),
                                relevance_score=row.get("similarity", 0.0),
                            ))
                        ranked = self._rank_case_studies(studies, context, top_k)
                        if ranked:
                            return ranked
                except Exception as e:
                    logger.warning("pgvector search failed, falling back to keyword: %s", e)

        return self._rank_case_studies(LOCAL_CASE_STUDIES, context, top_k)

    def _rank_case_studies(
        self,
        studies: list[CaseStudy],
        context: CaseStudyMatchContext,
        top_k: int,
    ) -> list[CaseStudy]:
        ranked: list[CaseStudy] = []
        weak_count = 0
        for case in studies:
            matched = _score_case_study(case, context)
            if matched.relevance_tier == "weak":
                weak_count += 1
                continue
            ranked.append(matched)

        ranked.sort(
            key=lambda c: (
                0 if c.relevance_tier == "exact" else 1,
                -c.relevance_score,
                c.city,
                c.title,
            )
        )
        result = ranked[:top_k]
        self.last_case_retrieval = CaseRetrievalAudit(
            query_city=context.city,
            query_sectors=context.sectors,
            query_policies=context.policies,
            returned_count=len(result),
            omitted_weak_count=weak_count,
            retrieval_mode="strict",
        )
        return result

    async def list_case_studies(
        self,
        city: str | None = None,
        sector: str | None = None,
        policy: str | None = None,
    ) -> list[dict[str, Any]]:
        studies = await self.search_case_studies([], city=city, sector=sector, policy=policy, top_k=50)
        if not city and not sector and not policy:
            studies = LOCAL_CASE_STUDIES
        return [study.model_dump() for study in studies]


def build_case_study_context(
    parsed: ParsedScenario | None = None,
    original_query: str = "",
    city: str | None = None,
    sectors: list[str] | None = None,
    policies: list[str] | None = None,
    keywords: list[str] | str | None = None,
) -> CaseStudyMatchContext:
    if parsed:
        city = parsed.city
        sectors = [
            sector
            for sector, delta in sorted(
                parsed.sector_deltas.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )
            if abs(delta) > 0
        ]
        policies = list(parsed.policies_active)
        base_keywords: list[str] = list(parsed.keywords)
        sector_directions = {
            sector: "positive" if delta > 0 else "negative" if delta < 0 else "mixed"
            for sector, delta in parsed.sector_deltas.items()
            if abs(delta) > 0
        }
    else:
        base_keywords = []
        sector_directions = {}

    if isinstance(keywords, str):
        base_keywords.extend(keywords.split())
    elif keywords:
        base_keywords.extend(str(word) for word in keywords)
    if original_query:
        base_keywords.extend(original_query.split())
    if city:
        base_keywords.append(city)
    base_keywords.extend(sectors or [])
    base_keywords.extend(policies or [])

    return CaseStudyMatchContext(
        city=city,
        sectors=_unique([_normal_sector(sector) for sector in (sectors or []) if sector]),
        policies=_unique([policy for policy in (policies or []) if policy]),
        keywords=_unique([word for word in base_keywords if word]),
        sector_directions=sector_directions,
    )


def _score_case_study(case: CaseStudy, context: CaseStudyMatchContext) -> CaseStudy:
    query_city = _normal_city(context.city)
    case_city = _normal_city(case.city)
    matched_city = bool(query_city and (query_city == case_city or query_city in case_city or case_city in query_city))
    query_sectors = {_normal_sector(sector) for sector in context.sectors}
    case_sectors = {_normal_sector(sector) for sector in case.sectors}
    query_policies = {_normal_policy(policy) for policy in context.policies}
    case_policies = {_normal_policy(policy) for policy in case.policies}
    matched_sectors = sorted(query_sectors & case_sectors)
    matched_policies = [
        policy
        for policy in case.policies
        if _normal_policy(policy) in query_policies
    ]
    haystack = " ".join([case.city, case.title, case.description, *case.tags, *case.sectors, *case.policies]).lower()
    keyword_hits = {
        token
        for token in (_normal_token(word) for word in context.keywords)
        if len(token) > 2 and token.replace("_", " ") in haystack
    }

    has_topic_filter = bool(query_sectors or query_policies)
    has_topic_match = bool(matched_sectors or matched_policies)
    primary_sectors = set(context.sectors[:1])
    tier: str = "weak"
    reasons: list[str] = []
    score = 0.0

    if matched_city:
        reasons.append("Same city")
    for sector in matched_sectors:
        reasons.append(_sector_label(sector))
    reasons.extend(matched_policies)

    if has_topic_filter:
        if matched_city and has_topic_match:
            tier = "exact"
            score = 100.0
        elif matched_policies or (set(matched_sectors) & primary_sectors):
            tier = "related"
            score = 55.0
        elif matched_city and len(keyword_hits) >= 2:
            tier = "related"
            score = 45.0
    elif matched_city:
        tier = "exact"
        score = 70.0

    if tier != "weak":
        score += len(matched_sectors) * 12.0
        score += len(matched_policies) * 16.0
        score += min(len(keyword_hits), 6) * 2.0
        if case.relevance_score:
            score += min(float(case.relevance_score), 1.0) * 5.0

    return case.model_copy(update={
        "relevance_score": score,
        "match_reasons": _unique(reasons),
        "relevance_tier": tier,
        "matched_city": matched_city,
        "matched_sectors": matched_sectors,
        "matched_policies": matched_policies,
    })


def _normal_city(value: str | None) -> str:
    if not value:
        return ""
    return value.lower().replace(" ", "_").replace("-", "_")


def _city_lookup_value(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("_", " ")


def _normal_sector(value: str) -> str:
    return value.lower().replace(" ", "_").replace("&", "and")


def _normal_policy(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _normal_token(value: str) -> str:
    return value.lower().strip(".,:;!?()[]{}'\"")


def _sector_label(value: str) -> str:
    return value.replace("_", " ").title().replace("It Ites", "IT/ITES")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _snapshot_from_row(row: dict[str, Any]) -> SnapshotData:
    manifest: dict[str, SourceStatus] = {}
    raw_manifest = row.get("source_manifest") or {}
    if isinstance(raw_manifest, dict):
        for domain, payload in raw_manifest.items():
            if isinstance(payload, dict):
                try:
                    manifest[domain] = SourceStatus(**payload)
                except Exception:
                    continue
    if not manifest:
        manifest = build_demo_manifest()
    snapshot_at = _parse_dt(row.get("snapshot_at")) or datetime.now(timezone.utc)
    h3_cells = row.get("h3_cells") or {}
    if isinstance(h3_cells, list):
        h3_cells = {
            str(cell.get("h3Index") or cell.get("h3_index")): cell
            for cell in h3_cells
            if isinstance(cell, dict) and (cell.get("h3Index") or cell.get("h3_index"))
        }
    return SnapshotData(
        id=str(row.get("id") or uuid4()),
        city=str(row.get("city") or "bengaluru"),
        snapshot_at=snapshot_at,
        status=row.get("status") or ("degraded" if row.get("quality_score", 0) < 0.8 else "fresh"),
        quality_score=float(row.get("quality_score") or 0.0),
        source_manifest=manifest,
        h3_cells=h3_cells if isinstance(h3_cells, dict) else {},
        aggregate_metrics=row.get("aggregate_metrics") or {},
    )


def _known_challenges(city_type: str) -> list[str]:
    if "it" in city_type or "tech" in city_type:
        return ["traffic congestion", "housing affordability", "infrastructure stress"]
    if "port" in city_type:
        return ["logistics congestion", "flood exposure", "industrial land pressure"]
    if "manufacturing" in city_type or "pharma" in city_type:
        return ["industrial corridor pressure", "formal-informal job transition", "logistics demand"]
    return ["migration pressure", "basic services", "housing affordability"]


_db: DatabaseClient | None = None


async def get_db() -> DatabaseClient:
    global _db
    if _db is None:
        _db = DatabaseClient()
        await _db.connect()
    return _db
