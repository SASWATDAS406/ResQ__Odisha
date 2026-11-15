"""
ResQ-Odisha Machine Learning Engine.
Integrates Hugging Face Transformers pipelines for binary disaster triage
and zero-shot category classification with deterministic fallbacks.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("resq_odisha.ml")

# Emergency distress keywords in English and Odia script
EMERGENCY_KEYWORDS = [
    # English
    "trapped",
    "flood",
    "flooded",
    "water rising",
    "rising water",
    "cyclone",
    "roof",
    "injured",
    "bleeding",
    "help",
    "sos",
    "rescue",
    "drowning",
    "marooned",
    "stranded",
    "collapse",
    "collapsed",
    "rubble",
    "debris",
    "casualty",
    "crushed",
    "broken leg",
    "ambulance",
    "heart attack",
    "dying",
    "unconscious",
    "no food",
    "starving",
    "drinking water",
    "baby food",
    "inundated",
    "submerged",
    "storm surge",
    "tidal surge",
    "wash away",
    "washed away",
    # Odia (ଓଡ଼ିଆ)
    "ବନ୍ୟା",
    "ବାତ୍ୟା",
    "ପାଣି",
    "ଉଦ୍ଧାର",
    "ସାହାଯ୍ୟ",
    "ଆହତ",
    "ରକ୍ତ",
    "ରକ୍ତସ୍ରାବ",
    "ଡଙ୍ଗା",
    "ବୁଡ଼ି",
    "ଭୁଶୁଡି",
    "ଛାତ",
    "କାନ୍ଥ",
    "ଭୋକ",
    "ଖାଦ୍ୟ",
    "ପିଇବା ପାଣି",
    "ବିପଦ",
]

# Casual / non-emergency indicators
CASUAL_KEYWORDS = [
    "hello",
    "hi",
    "test",
    "testing",
    "exam",
    "college",
    "result",
    "cricket",
    "movie",
    "score",
    "forecast tomorrow",
    "check status",
    "just checking",
    "good morning",
    "how are you",
]


class DisasterMLEngine:
    _instance: Optional["DisasterMLEngine"] = None

    def __new__(cls) -> "DisasterMLEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_models()
        return cls._instance

    def _initialize_models(self) -> None:
        """Attempt to load Hugging Face pipelines with safe hardware detection and fallbacks."""
        self.device = -1
        self.binary_classifier = None
        self.zero_shot_classifier = None
        self.is_hf_ready = False

        try:
            import torch
            from transformers import pipeline

            self.device = 0 if torch.cuda.is_available() else -1
            logger.info("Initializing Hugging Face models on device: %s", self.device)

            # Model 1: Binary Emergency Filter
            logger.info("Loading binary disaster classifier: CollinMa/disaster-tweets-bert...")
            self.binary_classifier = pipeline(
                "text-classification",
                model="CollinMa/disaster-tweets-bert",
                device=self.device,
            )

            # Model 2: Zero-Shot Triage Categorizer
            logger.info("Loading zero-shot classifier: typeform/distilbert-base-uncased-mnli...")
            self.zero_shot_classifier = pipeline(
                "zero-shot-classification",
                model="typeform/distilbert-base-uncased-mnli",
                device=self.device,
            )

            self.is_hf_ready = True
            logger.info("Both Hugging Face models loaded successfully.")
        except Exception as exc:
            logger.warning(
                "Hugging Face models could not be loaded directly (%s). "
                "Engaging resilient deterministic NLP triage engine.",
                exc,
            )
            self.is_hf_ready = False

    def _contains_emergency_keyword(self, text: str) -> bool:
        """Check if distress keywords are present in English or Odia."""
        text_lower = text.lower()
        for kw in EMERGENCY_KEYWORDS:
            if kw in text_lower or kw in text:
                return True
        return False

    def _contains_casual_keyword(self, text: str) -> bool:
        """Check if message is trivial casual chatter using word boundaries."""
        text_lower = text.lower().strip()
        pattern = r'\b(hello|hi|hey|test|testing|exam|college|result|cricket|movie|score|forecast tomorrow|good morning|how are you|just checking)\b'
        return bool(re.search(pattern, text_lower))

    def _heuristic_categorize(self, text: str) -> tuple[str, float]:
        """Categorize distress message into the 4 target emergency categories."""
        text_lower = text.lower()

        scores = {
            "medical emergency": 0.0,
            "structural collapse": 0.0,
            "flood rescue": 0.0,
            "food and drinking water": 0.0,
        }

        # Medical emergency indicators
        med_words = ["injur", "bleed", "wound", "leg", "arm", "fracture", "doctor", "ambulance",
                     "unconscious", "heart", "die", "dying", "casualt", "hospital", "patient", "ଆହତ", "ରକ୍ତ", "ଡାକ୍ତର"]
        for w in med_words:
            if w in text_lower:
                scores["medical emergency"] += 2.5

        # Structural collapse indicators
        struct_words = ["roof", "tin roof", "wall", "collaps", "crush", "debris", "fell",
                        "rubble", "building", "house fell", "buried", "ଛାତ", "କାନ୍ଥ", "ଭୁଶୁଡି"]
        for w in struct_words:
            if w in text_lower:
                scores["structural collapse"] += 2.5

        # Flood rescue indicators
        flood_words = ["flood", "water", "rising", "boat", "trapped", "stranded", "marooned",
                       "drown", "submerged", "inundat", "river", "surge", "beach", "sea", "ବନ୍ୟା", "ପାଣି", "ଉଦ୍ଧାର", "ଡଙ୍ଗା"]
        for w in flood_words:
            if w in text_lower:
                scores["flood rescue"] += 2.0

        # Food and water indicators
        food_words = ["food", "drink", "water", "starv", "hungry", "ration", "baby food", "milk",
                      "chuda", "guda", "biscuit", "thirst", "ଖାଦ୍ୟ", "ଭୋକ", "ପିଇବା ପାଣି"]
        for w in food_words:
            if w in text_lower:
                scores["food and drinking water"] += 2.0

        best_category = max(scores, key=scores.get)  # type: ignore
        best_score = scores[best_category]

        if best_score == 0.0:
            # Default to flood rescue in coastal cyclone environment
            best_category = "flood rescue"
            confidence = 0.75
        else:
            confidence = min(0.98, 0.70 + (best_score * 0.05))

        return best_category, round(confidence, 3)

    def analyze_sos(self, text: str, weather: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze incoming SOS message with binary verification, zero-shot categorization,
        dispatch unit mapping, and weather context escalation.
        """
        weather = weather or {}
        text_clean = text.strip()
        has_emergency_keyword = self._contains_emergency_keyword(text_clean)
        is_casual = self._contains_casual_keyword(text_clean)

        # Step 1: Binary Emergency Verification
        hf_detected_disaster = False
        hf_confidence = 0.90

        if self.is_hf_ready and self.binary_classifier is not None:
            try:
                result = self.binary_classifier(text_clean)[0]
                label = str(result.get("label", "")).upper()
                score = float(result.get("score", 0.85))
                hf_confidence = score

                # Critical label handling: LABEL_1, 1, or DISASTER = True
                if label in ("LABEL_1", "1", "DISASTER"):
                    hf_detected_disaster = True
                elif label in ("LABEL_0", "0", "NOT_DISASTER"):
                    hf_detected_disaster = False
                else:
                    hf_detected_disaster = score > 0.5
            except Exception as e:
                logger.error("Error executing binary HF classifier: %s", e)
                hf_detected_disaster = has_emergency_keyword

        # Combine with deterministic keyword heuristic
        is_emergency = hf_detected_disaster or has_emergency_keyword

        # If it is casual chatter and contains no distress keywords, filter out
        if is_casual and not has_emergency_keyword:
            is_emergency = False

        if not is_emergency:
            return {
                "is_emergency": False,
                "urgency_score": 1,
                "category": "NON_EMERGENCY",
                "confidence": round(hf_confidence if not hf_detected_disaster else 0.92, 2),
                "dispatch_unit": "None (Automated Advisory Sent)",
                "advisory_key": "GENERAL_STORM",
                "weather_boosted": False,
                "model_engine_status": "ONLINE (Local HF)" if self.is_hf_ready else "ONLINE (Heuristic NLP)",
            }

        # Step 2: Zero-Shot Categorization
        candidate_labels = [
            "flood rescue",
            "medical emergency",
            "structural collapse",
            "food and drinking water",
        ]

        assigned_category = "flood rescue"
        category_confidence = 0.88

        if self.is_hf_ready and self.zero_shot_classifier is not None:
            try:
                zs_result = self.zero_shot_classifier(text_clean, candidate_labels)
                assigned_category = zs_result["labels"][0]
                category_confidence = round(float(zs_result["scores"][0]), 2)
            except Exception as e:
                logger.error("Error executing zero-shot classifier: %s", e)
                assigned_category, category_confidence = self._heuristic_categorize(text_clean)
        else:
            assigned_category, category_confidence = self._heuristic_categorize(text_clean)

        # Step 3: Base Urgency & Dispatch Asset Mapping
        if assigned_category == "medical emergency":
            base_urgency = 5
            dispatch_unit = "ODRAF Medical Rapid Response & 108 Ambulance"
            advisory_key = "CYCLONE"
        elif assigned_category == "structural collapse":
            base_urgency = 4
            dispatch_unit = "NDRF Heavy Cutting & Search Team"
            advisory_key = "CYCLONE"
        elif assigned_category == "flood rescue":
            base_urgency = 4
            dispatch_unit = "ODRAF Inflatable Power Boat Unit"
            advisory_key = "FLOOD"
        elif assigned_category == "food and drinking water":
            base_urgency = 3
            dispatch_unit = "Block Civil Supply & Dry Ration Team"
            advisory_key = "FLOOD"
        else:
            base_urgency = 3
            dispatch_unit = "OSDMA First Response Unit"
            advisory_key = "CYCLONE"

        # Step 4: Weather Context Escalation
        rainfall = float(weather.get("rainfall_mm", 0.0))
        wind = float(weather.get("wind_kmh", 0.0))
        alert_level = str(weather.get("alert_level", "")).upper()

        weather_boosted = False
        urgency_score = base_urgency

        if rainfall >= 40.0 or wind >= 70.0 or alert_level == "RED":
            urgency_score = min(5, base_urgency + 1)
            weather_boosted = True

        return {
            "is_emergency": True,
            "urgency_score": urgency_score,
            "category": assigned_category,
            "confidence": category_confidence,
            "dispatch_unit": dispatch_unit,
            "advisory_key": advisory_key,
            "weather_boosted": weather_boosted,
            "model_engine_status": "ONLINE (Local HF)" if self.is_hf_ready else "ONLINE (Heuristic NLP)",
        }


# Global singleton instance
ml_engine = DisasterMLEngine()
