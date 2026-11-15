"""
Bilingual (English + Odia) OSDMA Safety SOPs & Disaster Advisories.
Tailored for Bay of Bengal Cyclones, Mahanadi Basin Floods, and Coastal Storm Surges.
"""

from typing import Any, Dict

DEFAULT_HELPLINES_EN = [
    {"name": "OSDMA State Control Room", "number": "1070"},
    {"name": "Emergency Police / Fire / Ambulance", "number": "112"},
    {"name": "Special Relief Commissioner (SRC)", "number": "0674-2534177"},
    {"name": "ODRAF Disaster Search & Rescue", "number": "0674-2536721"},
]

DEFAULT_HELPLINES_OD = [
    {"name": "ଓସ୍‌ଡମା (OSDMA) ରାଜ୍ୟ ନିୟନ୍ତ୍ରଣ କକ୍ଷ", "number": "1070"},
    {"name": "ଜରୁରୀକାଳୀନ ପୋଲିସ / ଅଗ୍ନିଶମ / ଆମ୍ବୁଲାନ୍ସ", "number": "112"},
    {"name": "ସ୍ୱତନ୍ତ୍ର ରିଲିଫ୍ କମିଶନର (SRC) ହେଲ୍ପଲାଇନ୍", "number": "0674-2534177"},
    {"name": "ଓଡ୍ରାଫ୍ (ODRAF) ବିପର୍ଯ୍ୟୟ ଉଦ୍ଧାରକାରୀ ଦଳ", "number": "0674-2536721"},
]

ADVISORIES: Dict[str, Dict[str, Any]] = {
    "CYCLONE": {
        "en": {
            "title": "OSDMA Cyclone & High Velocity Gale Advisory",
            "alert_banner": "HIGH-SEVERITY CYCLONIC STORM APPROACHING: EVACUATE TO DESIGNATED PUCCA SHELTER IMMEDIATELY",
            "immediate_actions": [
                "Move immediately to the nearest OSDMA Multipurpose Cyclone Shelter (MCS) or a reinforced concrete building.",
                "Turn off the main electrical supply switch and disconnect domestic LPG cooking cylinders.",
                "Keep away from glass doors, large windows, asbestos sheets, and tin roofing that can become airborne projectiles.",
                "Do not leave shelter during the 'Eye of the Cyclone' lull; extreme opposite gales will resume violently within 30-45 minutes.",
            ],
            "before_disaster_checklist": [
                "Pack dry non-perishable rations (Chuda, Guda, biscuits), chlorine tablets, and 3 days of potable water in waterproof containers.",
                "Store essential identity cards (Aadhaar, Ration Card), land records, and prescription medicines in zip-locked plastic bags.",
                "Keep fully charged mobile phones, power banks, battery-powered transistor radios, and LED emergency torches ready.",
            ],
            "after_disaster_safety": [
                "Beware of snapped, sagged, or submerged electric cables; assume all dangling wires are live until certified dead by CESU/TPCODL.",
                "Drink only halogen-treated or boiled water (rolling boil for 10+ minutes) to prevent waterborne cholera and diarrhea epidemics.",
                "Watch out for venomous snakes and reptiles taking refuge inside flooded homesteads, bushes, and fallen tree branches.",
            ],
            "donts": [
                "Do NOT venture out towards the seashore, beaches, or riverbanks to witness tidal swells, waves, or storm surges.",
                "Do NOT spread unverified rumors, forwards, or audio clips on social media; rely solely on official IMD/OSDMA bulletins.",
                "Do NOT drive vehicles, two-wheelers, or walk through fast-flowing tidal surge water across inundated coastal causeways.",
            ],
            "emergency_helplines": DEFAULT_HELPLINES_EN,
        },
        "od": {
            "title": "ଓସ୍‌ଡମା (OSDMA) ବାତ୍ୟା ଓ ଝଡ଼ବାତ୍ୟା ସୁରକ୍ଷା ନିର୍ଦ୍ଦେଶାବଳୀ",
            "alert_banner": "ଉଚ୍ଚ-ତୀବ୍ରତା ବାତ୍ୟା ସତର୍କତା: ତୁରନ୍ତ ନିକଟସ୍ଥ ପକ୍କା ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀକୁ ସ୍ଥାନାନ୍ତରିତ ହୁଅନ୍ତୁ",
            "immediate_actions": [
                "ତୁରନ୍ତ ନିକଟସ୍ଥ ଓସ୍‌ଡମା (OSDMA) ବହୁମୁଖୀ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀ କିମ୍ବା ପକ୍କା ଛାତ ଘରକୁ ଚାଲିଯାଆନ୍ତୁ ।",
                "ଘରର ମୁଖ୍ୟ ବିଦ୍ୟୁତ୍ ସ୍ୱିଚ୍ (ମେନ୍ ସୁଇଚ୍) ବନ୍ଦ କରନ୍ତୁ ଏବଂ ରନ୍ଧନ ଗ୍ୟାସ୍ (LPG) ସିଲିଣ୍ଡରର ରେଗୁଲେଟର୍ ଖୋଲି ବନ୍ଦ କରନ୍ତୁ ।",
                "କାଚ ଝରକା, ଟିଣ ଛାତ କିମ୍ବା ଆଜବେଷ୍ଟସ ପାଖରୁ ଦୂରରେ ରୁହନ୍ତୁ, କାରଣ ତୀବ୍ର ପବନରେ ଏଗୁଡ଼ିକ ଉଡ଼ି ଆଘାତ ଦେଇପାରେ ।",
                "ବାତ୍ୟାର କେନ୍ଦ୍ର (Eye of Cyclone) ସମୟରେ ପବନ ଥମିଗଲେ ମଧ୍ୟ ବାହାରକୁ ଆସନ୍ତୁ ନାହିଁ; ଅଳ୍ପ ସମୟ ପରେ ବିପରୀତ ଦିଗରୁ ପ୍ରଚଣ୍ଡ ବେଗରେ ପବନ ଆରମ୍ଭ ହେବ ।",
            ],
            "before_disaster_checklist": [
                "ଶୁଖିଲା ଖାଦ୍ୟ (ଚୂଡ଼ା, ଗୁଡ଼, ବିସ୍କୁଟ), ହାଲୋଜେନ୍ ଟାବ୍ଲେଟ୍ ଏବଂ ୩ ଦିନ ପାଇଁ ପିଇବା ପାଣି ଜଳରୋଧକ ମୁଣାରେ ସାଇତି ରଖନ୍ତୁ ।",
                "ଜରୁରୀ ପରିଚୟ ପତ୍ର (ଆଧାର କାର୍ଡ, ରାସନ କାର୍ଡ), ଜମି ପଟ୍ଟା ଏବଂ ନିୟମିତ ଔଷଧକୁ ପ୍ଲାଷ୍ଟିକ୍ ଜିପ୍-ଲକ୍ ବ୍ୟାଗ୍‌ରେ ସୁରକ୍ଷିତ ରଖନ୍ତୁ ।",
                "ମୋବାଇଲ୍ ଫୋନ୍ ଓ ପାୱାର୍ ବ୍ୟାଙ୍କ୍ ସମ୍ପୂର୍ଣ୍ଣ ଚାର୍ଜ ରଖନ୍ତୁ ଏବଂ ବ୍ୟାଟେରୀ ଚାଳିତ ରେଡ଼ିଓ ଓ ଟର୍ଚ୍ଚ ପ୍ରସ୍ତୁତ ରଖନ୍ତୁ ।",
            ],
            "after_disaster_safety": [
                "ଛିଣ୍ଡି ପଡ଼ିଥିବା କିମ୍ବା ଝୁଲୁଥିବା ବିଦ୍ୟୁତ୍ ତାରକୁ କେବେବି ସ୍ପର୍ଶ କରନ୍ତୁ ନାହିଁ ଏବଂ ଅନ୍ୟମାନଙ୍କୁ ସତର୍କ କରାନ୍ତୁ ।",
                "କେବଳ ଫୁଟନ୍ତା ପାଣି (୧୦ ମିନିଟ୍ ଫୁଟିଥିବା) କିମ୍ବା ହାଲୋଜେନ୍ ବିଶୋଧିତ ପାଣି ପିଅନ୍ତୁ, ଯାହାଦ୍ୱାରା ଝାଡ଼ାବାନ୍ତି ରୋକାଯାଇପାରିବ ।",
                "ଭଙ୍ଗା ଘର, ଝାଙ୍କି ଜଙ୍ଗଲ ଏବଂ ଉପୁଡ଼ି ପଡ଼ିଥିବା ଗଛ ଡାଳରେ ବିଷାକ୍ତ ସାପ ରହିବାର ଆଶଙ୍କା ଥିବାରୁ ସାପ କାମୁଡ଼ା ପ୍ରତି ଅତ୍ୟନ୍ତ ସତର୍କ ରୁହନ୍ତୁ ।",
            ],
            "donts": [
                "ସମୁଦ୍ର କୂଳ, ବେଳାଭୂମି କିମ୍ବା ନଦୀ ପଠାକୁ ଢେଉ ବା ଝଡ଼ ଦେଖିବା ପାଇଁ ଯାଆନ୍ତୁ ନାହିଁ ।",
                "ସୋସିଆଲ୍ ମିଡିଆରେ ଅଣ-ପ୍ରମାଣିତ ଗୁଜବ, ଭୁଲ୍ ତଥ୍ୟ କିମ୍ବା ଅଡିଓ ବାର୍ତ୍ତା ପ୍ରସାର କରନ୍ତୁ ନାହିଁ; କେବଳ ସରକାରୀ ବୁଲେଟିନ୍ ବିଶ୍ୱାସ କରନ୍ତୁ ।",
                "ପାଣି ଜମିଥିବା ରାସ୍ତା, ପୋଲ କିମ୍ବା କଲଭର୍ଟ ଉପରେ ଗାଡ଼ି ଚଳାଇବାକୁ ଚେଷ୍ଟା କରନ୍ତୁ ନାହିଁ ।",
            ],
            "emergency_helplines": DEFAULT_HELPLINES_OD,
        },
    },
    "FLOOD": {
        "en": {
            "title": "OSDMA Deltaic Basin & Riverine Flood Safety Protocol",
            "alert_banner": "FLOOD ALERT: RIVER DISCHARGE & INUNDATION RISING RAPIDLY — RETREAT TO ELEVATED GROUND",
            "immediate_actions": [
                "Evacuate immediately to higher terrain, embankment shelters, or the nearest two-story public building.",
                "Never walk, swim, or wade through moving floodwaters; 15 cm of fast-moving water can knock an adult down.",
                "Untie domestic livestock, cattle, and pets so they can swim to natural high ridges and survival mounds.",
                "Signal rescue boats (ODRAF/NDRF) using bright cloth, whistles, or torches from rooftops.",
            ],
            "before_disaster_checklist": [
                "Store drinking water in sealed jerry cans and keep water purification halogen drops handy.",
                "Elevate household electrical appliances, bedding, grain sacks, and fertilizer bags above historical flood levels.",
                "Prepare bamboo poles, synthetic ropes, and inflated vehicle tubes as emergency flotation aids.",
            ],
            "after_disaster_safety": [
                "Drink strictly boiled or chlorinated water; do not drink from submerged tube-wells until disinfected with bleaching powder.",
                "Inspect house foundations, mud walls, and pillars for structural weakness before stepping inside.",
                "Carry a long stick when walking through receding mud and stagnant water to ward off reptiles and check deep sinkholes.",
            ],
            "donts": [
                "Do NOT enter damaged buildings or breach embankments to catch fish during rising river discharge.",
                "Do NOT consume food items that have come in direct contact with muddy floodwaters.",
                "Do NOT reconnect electrical mains until certified completely dry and inspected by a qualified electrician.",
            ],
            "emergency_helplines": DEFAULT_HELPLINES_EN,
        },
        "od": {
            "title": "ଓସ୍‌ଡମା (OSDMA) ବନ୍ୟା ଓ ଜଳବନ୍ଦୀ ସୁରକ୍ଷା ନିର୍ଦ୍ଦେଶାବଳୀ",
            "alert_banner": "ବନ୍ୟା ସତର୍କତା ସୂଚନା: ନଦୀର ଜଳସ୍ତର ଦ୍ରୁତ ଗତିରେ ବୃଦ୍ଧି ପାଉଛି — ତୁରନ୍ତ ଉଚ୍ଚ ସ୍ଥାନକୁ ଚାଲିଯାଆନ୍ତୁ",
            "immediate_actions": [
                "ବିଳମ୍ବ ନକରି ଉଚ୍ଚ ସ୍ଥାନ, ନଦୀବନ୍ଧ କିମ୍ବା ନିକଟସ୍ଥ ଦୁଇ ମହଲା କୋଠାକୁ ଚାଲିଯାଆନ୍ତୁ ।",
                "ପ୍ରବାହିତ ବନ୍ୟା ପାଣିରେ ପହଁରିବା କିମ୍ବା ଚାଲିବା ଚେଷ୍ଟା କରନ୍ତୁ ନାହିଁ; ୬ ଇଞ୍ଚର ପ୍ରଖର ସ୍ରୋତ ମଧ୍ୟ ମଣିଷକୁ ଭସାଇ ନେଇପାରେ ।",
                "ଗୃହପାଳିତ ପଶୁପକ୍ଷୀ ଓ ଗାଈଗୋରୁଙ୍କୁ ଖୁଣ୍ଟରୁ ଫିଟାଇ ଦିଅନ୍ତୁ ଯେପରି ସେମାନେ ଉଚ୍ଚ ସ୍ଥାନକୁ ପହଁରି ଯାଇପାରିବେ ।",
                "ଘର ଛାତ ଉପରୁ ଉଜ୍ଜ୍ୱଳ ରଙ୍ଗର କପଡ଼ା, ହୁଇସିଲ୍ କିମ୍ବା ଟର୍ଚ୍ଚ ଲାଇଟ୍ ଦେଖାଇ ଓଡ୍ରାଫ୍/ଏନ୍‌ଡିଆର୍‌ଏଫ୍ ଡଙ୍ଗାକୁ ସଙ୍କେତ ଦିଅନ୍ତୁ ।",
            ],
            "before_disaster_checklist": [
                "ବିଶୁଦ୍ଧ ପିଇବା ପାଣି ବୋତଲରେ ଭରି ରଖନ୍ତୁ ଏବଂ ଜଳ ବିଶୋଧନ ହାଲୋଜେନ୍ ଟାବ୍ଲେଟ୍ ସାଙ୍ଗରେ ରଖନ୍ତୁ ।",
                "ଘରର ବୈଦ୍ୟୁତିକ ସରଞ୍ଜାମ, ଧାନ ବସ୍ତା ଓ ମୂଲ୍ୟବାନ ଜିନିଷକୁ ଚାଳ ଉପରେ କିମ୍ବା ଉଚ୍ଚ ମଞ୍ଚାରେ ଉଠାଇ ରଖନ୍ତୁ ।",
                "ବାଉଁଶ ବାଉଁଶି, ମୋଟା ଦଉଡ଼ି ଏବଂ ଟ୍ୟୁବ୍ ଭଳି ପାଣିରେ ଭାସିବା ସାମଗ୍ରୀ ପ୍ରସ୍ତୁତ ରଖନ୍ତୁ ।",
            ],
            "after_disaster_safety": [
                "ବନ୍ୟା ପାଣି ବୁଡ଼ିଥିବା ନଳକୂଅର ପାଣି ବିଲକୁଲ୍ ପିଅନ୍ତୁ ନାହିଁ; କେବଳ ବ୍ଲିଚିଂ ପାଉଡର ପକାଯାଇଥିବା କିମ୍ବା ଫୁଟନ୍ତା ପାଣି ବ୍ୟବହାର କରନ୍ତୁ ।",
                "ପାଣି ଛାଡ଼ିବା ପରେ ଘରେ ପଶିବା ପୂର୍ବରୁ କାନ୍ଥ ଏବଂ ଖୁଣ୍ଟ ସୁରକ୍ଷିତ ଅଛି କି ନାହିଁ ଭଲଭାବେ ଯାଞ୍ଚ କରନ୍ତୁ ।",
                "କାଦୁଅ କିମ୍ବା ଜମିଥିବା ପାଣିରେ ଚାଲିବା ବେଳେ ଏକ ଲମ୍ବା ବାଡ଼ି ହାତରେ ଧରନ୍ତୁ, ଯାହା ସାପ ଓ ଗାତରୁ ରକ୍ଷା କରିବ ।",
            ],
            "donts": [
                "ବନ୍ୟା ସମୟରେ ମାଛ ଧରିବା ପାଇଁ ନଦୀବନ୍ଧ, ଘାଇ କିମ୍ବା ସ୍ରୋତ ଭିତରକୁ ଯାଆନ୍ତୁ ନାହିଁ ।",
                "ବନ୍ୟା ପାଣି ସଂସ୍ପର୍ଶରେ ଆସିଥିବା କୌଣସି ଖାଦ୍ୟ ଦ୍ରବ୍ୟ ଗ୍ରହଣ କରନ୍ତୁ ନାହିଁ ।",
                "ଓଦା ଥିବା ବୈଦ୍ୟୁତିକ ଉପକରଣ କିମ୍ବା ସୁଇଚ୍ କୁ ବିପଦମୁକ୍ତ ପ୍ରମାଣିତ ନହେବା ପର୍ଯ୍ୟନ୍ତ ଚଳାନ୍ତୁ ନାହିଁ ।",
            ],
            "emergency_helplines": DEFAULT_HELPLINES_OD,
        },
    },
    "GENERAL_STORM": {
        "en": {
            "title": "OSDMA Severe Weather & Citizen Advisory Standard SOP",
            "alert_banner": "WEATHER WATCH: SQUALLY WINDS AND RAIN SPELLS ACROSS COASTAL ODISHA — MAINTAIN VIGILANCE",
            "immediate_actions": [
                "Seek indoor shelter in a permanent pucca structure away from aged trees, hoardings, and tin sheds.",
                "Secure all loose outdoor objects, metal roof sheets, signboards, and rooftop water tanks.",
                "Charge emergency communication devices, phones, and power banks; tune into All India Radio Cuttack/Puri.",
                "Ensure emergency contacts and the 112 toll-free helpline are easily accessible.",
            ],
            "before_disaster_checklist": [
                "Inspect household drainage outlets to prevent localized waterlogging inside living premises.",
                "Stock basic home first-aid supplies, antiseptic lotions, and necessary prescription medications.",
                "Keep cash and digital wallet balance ready in case automated teller machines (ATMs) lose network connectivity.",
            ],
            "after_disaster_safety": [
                "Avoid stepping into open storm-water drains and localized urban water pools.",
                "Report broken telephone poles, fallen trees, and blocked arterial roads to the local municipality or Block Development Officer (BDO).",
                "Maintain hand hygiene and consume hot, freshly cooked meals to safeguard against gastroenteritis.",
            ],
            "donts": [
                "Do NOT take shelter underneath tall solitary trees or metal poles during thunder and lightning squalls.",
                "Do NOT spread unconfirmed panic rumors regarding cyclone landfall or dam gate openings.",
                "Do NOT operate faulty electrical appliances with wet hands.",
            ],
            "emergency_helplines": DEFAULT_HELPLINES_EN,
        },
        "od": {
            "title": "ଓସ୍‌ଡମା (OSDMA) ସାଧାରଣ ଝଡ଼ବର୍ଷା ଓ ନାଗରିକ ସୁରକ୍ଷା ମାର୍ଗଦର୍ଶିକା",
            "alert_banner": "ପାଣିପାଗ ସତର୍କତା: ଉପକୂଳ ଓଡ଼ିଶାରେ ଘଡ଼ଘଡ଼ି ସହ ବର୍ଷା ଓ ଝଟ୍‌କା ପବନ — ସତର୍କତା ଅବଲମ୍ବନ କରନ୍ତୁ",
            "immediate_actions": [
                "ପୁରୁଣା ଗଛ, ବିଜ୍ଞାପନ ବୋର୍ଡ ଓ ଟିଣ ଚାଳ ଠାରୁ ଦୂରରେ ରହି ପକ୍କା ଘର ଭିତରେ ଆଶ୍ରୟ ନିଅନ୍ତୁ ।",
                "ଛାତ କିମ୍ବା ଅଗଣାରେ ଥିବା ହାଲୁକା ସାମଗ୍ରୀ, ଟିଣ ଓ ପାଣି ଟାଙ୍କିକୁ ଦଉଡ଼ିରେ ଭଲଭାବେ ବାନ୍ଧି ସୁରକ୍ଷିତ କରନ୍ତୁ ।",
                "ମୋବାଇଲ୍ ଓ ଜରୁରୀ ଲାଇଟ୍ ଚାର୍ଜ ରଖନ୍ତୁ ଏବଂ ଆକାଶବାଣୀ କଟକ/ପୁରୀ କେନ୍ଦ୍ରର ଖବର ଶୁଣନ୍ତୁ ।",
                "ଜରୁରୀକାଳୀନ ହେଲ୍ପଲାଇନ୍ ୧୧୨ ଏବଂ ପରିବାରବର୍ଗଙ୍କ ସମ୍ପର୍କ ନମ୍ବର ହାତପାଆନ୍ତାରେ ରଖନ୍ତୁ ।",
            ],
            "before_disaster_checklist": [
                "ଘର ଚାରିପାଖର ଡ୍ରେନେଜ୍ ବ୍ୟବସ୍ଥା ସଫା ରଖନ୍ତୁ ଯେପରି ଘର ଭିତରକୁ ବର୍ଷା ପାଣି ନପଶିବ ।",
                "ଘରୋଇ ପ୍ରାଥମିକ ଚିକିତ୍ସା ବାକ୍ସ (ଫାଷ୍ଟ-ଏଡ୍), ଆଣ୍ଟିସେପ୍ଟିକ୍ ଓ ଦୈନନ୍ଦିନ ଔଷଧ ସାଇତି ରଖନ୍ତୁ ।",
                "ବିଦ୍ୟୁତ୍ କିମ୍ବା ନେଟୱାର୍କ ବିଭ୍ରାଟ ଆଶଙ୍କା ଥିବାରୁ କିଛି ନଗଦ ଟଙ୍କା ପାଖରେ ରଖନ୍ତୁ ।",
            ],
            "after_disaster_safety": [
                "ଖୋଲା ଡ୍ରେନ୍, ମ୍ୟାନହୋଲ୍ କିମ୍ବା ଜମିଥିବା ପାଣି ଭିତରେ ପଶନ୍ତୁ ନାହିଁ ।",
                "ଭାଙ୍ଗି ପଡ଼ିଥିବା ଗଛ କିମ୍ବା ଖୁଣ୍ଟ ବିଷୟରେ ସ୍ଥାନୀୟ ପୌରପାଳିକା କିମ୍ବା ବିଡିଓ ଅଫିସ୍‌କୁ ସୂଚନା ଦିଅନ୍ତୁ ।",
                "ହାତ ସଫା ରଖନ୍ତୁ ଏବଂ କେବଳ ସତେଜ ଗରମ ଖାଦ୍ୟ ଖାଆନ୍ତୁ ।",
            ],
            "donts": [
                "ବିଜୁଳି ଘଡ଼ଘଡ଼ି ମାରୁଥିବା ସମୟରେ ବଡ଼ ଗଛ କିମ୍ବା ବିଦ୍ୟୁତ୍ ଖୁଣ୍ଟ ତଳେ ଆଶ୍ରୟ ନିଅନ୍ତୁ ନାହିଁ ।",
                "ବାତ୍ୟା ବା ବନ୍ୟା ସମ୍ପର୍କରେ କୌଣସି ଅପପ୍ରଚାର କିମ୍ବା ଗୁଜବ ସୃଷ୍ଟି କରନ୍ତୁ ନାହିଁ ।",
                "ଓଦା ହାତରେ ବୈଦ୍ୟୁତିକ ସୁଇଚ୍ କିମ୍ବା ପ୍ଲଗ୍ ଛୁଅନ୍ତୁ ନାହିଁ ।",
            ],
            "emergency_helplines": DEFAULT_HELPLINES_OD,
        },
    },
}


def get_advisory(threat_type: str = "CYCLONE", lang: str = "en") -> Dict[str, Any]:
    """Retrieve structured bilingual safety guidelines for a specific hazard threat type."""
    normalized_key = threat_type.strip().upper()
    if "CYCLONE" in normalized_key or "STORM" in normalized_key or "SURGE" in normalized_key:
        key = "CYCLONE"
    elif "FLOOD" in normalized_key or "WATER" in normalized_key or "INUNDATION" in normalized_key:
        key = "FLOOD"
    else:
        key = "GENERAL_STORM"

    target_lang = "od" if lang.strip().lower() in ("od", "odia", "or") else "en"
    advisory_data = ADVISORIES.get(key, ADVISORIES["GENERAL_STORM"])
    return advisory_data.get(target_lang, advisory_data["en"])


def get_bilingual_advisories(threat_type: str = "CYCLONE") -> Dict[str, Any]:
    """Retrieve both English and Odia advisories in a single call."""
    normalized_key = threat_type.strip().upper()
    if "CYCLONE" in normalized_key or "STORM" in normalized_key or "SURGE" in normalized_key:
        key = "CYCLONE"
    elif "FLOOD" in normalized_key or "WATER" in normalized_key or "INUNDATION" in normalized_key:
        key = "FLOOD"
    else:
        key = "GENERAL_STORM"

    return {
        "en": ADVISORIES[key]["en"],
        "od": ADVISORIES[key]["od"],
        "advisory_key": key,
    }
