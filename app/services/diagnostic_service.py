"""Service for appliance diagnostic logic and troubleshooting."""

from typing import Dict, List, Optional, Tuple
from app.models.technician import ApplianceType


# Diagnostic knowledge base - symptoms, questions, and troubleshooting steps
DIAGNOSTIC_KNOWLEDGE = {
    ApplianceType.WASHER: {
        "common_symptoms": [
            "won't start",
            "won't spin",
            "not draining",
            "leaking water",
            "making loud noise",
            "shaking or vibrating",
            "door won't open",
            "not filling with water",
            "clothes still wet after cycle",
            "error code displayed"
        ],
        "diagnostic_questions": [
            "Is the washer plugged in and is the outlet working?",
            "Is the water supply turned on?",
            "Is the door or lid properly closed?",
            "What cycle were you trying to run?",
            "Are there any error codes displayed?",
            "How old is the washing machine?",
            "When did this problem first start?",
            "Is it a top-loader or front-loader?"
        ],
        "troubleshooting": {
            "won't start": [
                "Check that the washer is plugged in and the outlet has power",
                "Ensure the door or lid is completely closed and latched",
                "Check if the water supply valves are open",
                "Try resetting by unplugging for 1 minute, then plugging back in",
                "Check if the child lock feature is enabled"
            ],
            "not draining": [
                "Check the drain hose for kinks or clogs",
                "Clean the drain pump filter (usually at the front bottom)",
                "Ensure the drain hose height is correct (not too high)",
                "Check for small items that may have blocked the pump"
            ],
            "leaking water": [
                "Check door seal for damage or debris",
                "Inspect inlet hoses for cracks or loose connections",
                "Don't overload the washer",
                "Use the correct amount of HE detergent if required",
                "Check the drain hose connection"
            ],
            "making loud noise": [
                "Check if the washer is level using a spirit level",
                "Ensure shipping bolts have been removed (new washers)",
                "Check for foreign objects in the drum",
                "Avoid overloading the washer",
                "Check if anything is caught between the drum and tub"
            ]
        }
    },
    ApplianceType.DRYER: {
        "common_symptoms": [
            "won't start",
            "not heating",
            "takes too long to dry",
            "making loud noise",
            "drum not spinning",
            "shuts off too soon",
            "burning smell",
            "clothes too hot"
        ],
        "diagnostic_questions": [
            "Is it a gas or electric dryer?",
            "Is the dryer plugged in?",
            "When did you last clean the lint trap?",
            "Is the vent hose connected and clear?",
            "What heat setting are you using?",
            "How old is the dryer?",
            "Are there any error codes?"
        ],
        "troubleshooting": {
            "not heating": [
                "Check that the dryer is properly plugged in (electric needs 240V)",
                "For gas dryers, ensure the gas supply valve is open",
                "Clean the lint trap thoroughly",
                "Check and clean the dryer vent duct",
                "Make sure the vent isn't kinked or blocked"
            ],
            "takes too long to dry": [
                "Clean the lint trap before every load",
                "Check the vent system for blockages",
                "Don't overload the dryer",
                "Make sure clothes are properly spun in the washer first",
                "Check that the vent flap outside opens when dryer is running"
            ],
            "making loud noise": [
                "Check for coins or objects in the drum",
                "Ensure the dryer is level",
                "Check if the drum rollers need replacement",
                "Listen for where the noise is coming from"
            ]
        }
    },
    ApplianceType.REFRIGERATOR: {
        "common_symptoms": [
            "not cooling",
            "too cold",
            "making loud noise",
            "leaking water",
            "ice maker not working",
            "frost buildup",
            "water dispenser not working",
            "running constantly",
            "not running at all"
        ],
        "diagnostic_questions": [
            "Is the refrigerator plugged in?",
            "What temperature is it set to?",
            "How long has it been having issues?",
            "Is the freezer working properly?",
            "Are the condenser coils dirty?",
            "Is there frost buildup inside?",
            "Can you hear the compressor running?"
        ],
        "troubleshooting": {
            "not cooling": [
                "Check the temperature settings (should be 37°F fridge, 0°F freezer)",
                "Ensure vents inside aren't blocked by food items",
                "Clean the condenser coils (usually at the back or bottom)",
                "Check that the door seals are clean and sealing properly",
                "Make sure there's clearance around the unit for airflow"
            ],
            "ice maker not working": [
                "Check that the ice maker is turned on",
                "Ensure the water supply line is connected and valve is open",
                "Check the water filter - replace if older than 6 months",
                "Make sure the freezer is cold enough (0°F or below)",
                "Check for ice jams in the mechanism"
            ],
            "leaking water": [
                "Check if the defrost drain is clogged",
                "Inspect the water supply line for leaks",
                "Make sure the fridge is level (slightly higher in front)",
                "Check the drain pan under the unit"
            ]
        }
    },
    ApplianceType.DISHWASHER: {
        "common_symptoms": [
            "not cleaning dishes",
            "not draining",
            "leaking",
            "won't start",
            "making noise",
            "not drying dishes",
            "door won't latch",
            "bad odor"
        ],
        "diagnostic_questions": [
            "Is the dishwasher getting water?",
            "Are you using the right detergent?",
            "Is the drain clear?",
            "How are you loading the dishes?",
            "What cycle are you using?",
            "When was it last cleaned?"
        ],
        "troubleshooting": {
            "not cleaning dishes": [
                "Run hot water at the sink before starting the dishwasher",
                "Don't pre-rinse dishes, but scrape off large food particles",
                "Check that spray arms can spin freely",
                "Clean the filter at the bottom of the dishwasher",
                "Use fresh detergent and rinse aid",
                "Don't overload - water needs to reach all dishes"
            ],
            "not draining": [
                "Check and clean the filter and drain basket",
                "Ensure the garbage disposal knockout plug is removed",
                "Check the drain hose for kinks",
                "Run the garbage disposal before the dishwasher",
                "Clean the air gap if you have one"
            ],
            "bad odor": [
                "Run a cleaning cycle with dishwasher cleaner",
                "Clean the filter and drain area",
                "Wipe down the door gasket",
                "Leave the door slightly open between uses"
            ]
        }
    },
    ApplianceType.OVEN: {
        "common_symptoms": [
            "not heating",
            "uneven cooking",
            "temperature inaccurate",
            "burners won't ignite",
            "self-clean not working",
            "door won't open",
            "display not working"
        ],
        "diagnostic_questions": [
            "Is it a gas or electric oven?",
            "Which part isn't working - oven, stovetop, or both?",
            "Is the oven heating at all or just not reaching temperature?",
            "When did you last calibrate the temperature?",
            "Are there any error codes?"
        ],
        "troubleshooting": {
            "not heating": [
                "Check that the oven is properly plugged in",
                "For gas ovens, ensure the gas supply is on",
                "Try the broiler to see if it's just the bake element",
                "Check if the oven light comes on",
                "Make sure the oven isn't in self-clean mode"
            ],
            "uneven cooking": [
                "Use an oven thermometer to check actual temperature",
                "Avoid using dark pans which absorb more heat",
                "Allow proper air circulation - don't cover racks with foil",
                "Calibrate the oven temperature if needed",
                "Rotate dishes halfway through cooking"
            ],
            "burners won't ignite": [
                "Clean the burner caps and grates",
                "Make sure burner caps are properly seated",
                "Clean the igniter with a toothbrush",
                "Check if other burners work to isolate the issue"
            ]
        }
    },
    ApplianceType.HVAC: {
        "common_symptoms": [
            "not cooling",
            "not heating",
            "weak airflow",
            "strange noises",
            "bad smell",
            "constantly running",
            "short cycling",
            "high energy bills"
        ],
        "diagnostic_questions": [
            "Is it a central system, mini-split, or window unit?",
            "When was the filter last changed?",
            "Is the thermostat set correctly?",
            "Are all vents open?",
            "Is the outdoor unit running?",
            "How old is the system?"
        ],
        "troubleshooting": {
            "not cooling": [
                "Check and replace the air filter if dirty",
                "Make sure the thermostat is set to cool and below room temp",
                "Check that the outdoor unit isn't blocked by debris",
                "Ensure all vents inside are open and unobstructed",
                "Check if the outdoor unit fan is running",
                "Check circuit breakers for both indoor and outdoor units"
            ],
            "weak airflow": [
                "Replace the air filter",
                "Check if vents are open and unblocked",
                "Have ductwork inspected for leaks",
                "Make sure the blower fan is running"
            ],
            "strange noises": [
                "Rattling might mean loose panels - check and tighten",
                "Squealing could indicate belt issues",
                "Clicking at startup is normal; continuous clicking is not",
                "Banging might indicate a broken component"
            ]
        }
    }
}

# Default troubleshooting for appliances without specific entries
DEFAULT_TROUBLESHOOTING = [
    "Ensure the appliance is properly plugged in and receiving power",
    "Check if the circuit breaker hasn't tripped",
    "Look for any error codes or warning lights",
    "Try unplugging the appliance for 1 minute, then plugging it back in",
    "Review the user manual for troubleshooting guidance"
]


class DiagnosticService:
    """Service for appliance diagnostics and troubleshooting."""
    
    def __init__(self):
        self.knowledge = DIAGNOSTIC_KNOWLEDGE
    
    def get_supported_appliances(self) -> List[str]:
        """Get list of supported appliance types."""
        return ApplianceType.ALL_TYPES
    
    def normalize_appliance_type(self, user_input: str) -> Optional[str]:
        """
        Normalize user input to a standard appliance type.
        Handles common variations and typos.
        """
        user_input = user_input.lower().strip()
        
        # Direct mappings
        mappings = {
            # Washer variations
            "washer": ApplianceType.WASHER,
            "washing machine": ApplianceType.WASHER,
            "clothes washer": ApplianceType.WASHER,
            "laundry machine": ApplianceType.WASHER,
            
            # Dryer variations
            "dryer": ApplianceType.DRYER,
            "clothes dryer": ApplianceType.DRYER,
            "tumble dryer": ApplianceType.DRYER,
            
            # Refrigerator variations
            "refrigerator": ApplianceType.REFRIGERATOR,
            "fridge": ApplianceType.REFRIGERATOR,
            "refridgerator": ApplianceType.REFRIGERATOR,  # common misspelling
            
            # Dishwasher variations
            "dishwasher": ApplianceType.DISHWASHER,
            "dish washer": ApplianceType.DISHWASHER,
            
            # Oven variations
            "oven": ApplianceType.OVEN,
            "stove": ApplianceType.OVEN,
            "range": ApplianceType.OVEN,
            "cooktop": ApplianceType.OVEN,
            
            # Microwave variations
            "microwave": ApplianceType.MICROWAVE,
            "micro wave": ApplianceType.MICROWAVE,
            
            # HVAC variations
            "hvac": ApplianceType.HVAC,
            "ac": ApplianceType.HVAC,
            "air conditioner": ApplianceType.HVAC,
            "air conditioning": ApplianceType.HVAC,
            "heat pump": ApplianceType.HVAC,
            "furnace": ApplianceType.HVAC,
            "heating": ApplianceType.HVAC,
            "central air": ApplianceType.HVAC,
            
            # Others
            "garbage disposal": ApplianceType.GARBAGE_DISPOSAL,
            "disposal": ApplianceType.GARBAGE_DISPOSAL,
            "water heater": ApplianceType.WATER_HEATER,
            "hot water heater": ApplianceType.WATER_HEATER,
            "freezer": ApplianceType.FREEZER,
        }
        
        return mappings.get(user_input)
    
    def get_common_symptoms(self, appliance_type: str) -> List[str]:
        """Get common symptoms for an appliance type."""
        appliance_data = self.knowledge.get(appliance_type, {})
        return appliance_data.get("common_symptoms", [])
    
    def get_diagnostic_questions(self, appliance_type: str) -> List[str]:
        """Get diagnostic questions to ask for an appliance type."""
        appliance_data = self.knowledge.get(appliance_type, {})
        return appliance_data.get("diagnostic_questions", [])
    
    def get_troubleshooting_steps(
        self, 
        appliance_type: str, 
        symptom: str
    ) -> List[str]:
        """Get troubleshooting steps for a specific symptom."""
        appliance_data = self.knowledge.get(appliance_type, {})
        troubleshooting = appliance_data.get("troubleshooting", {})
        
        # Try to find matching symptom
        symptom_lower = symptom.lower()
        for key, steps in troubleshooting.items():
            if key in symptom_lower or symptom_lower in key:
                return steps
        
        # Return default if no specific match
        return DEFAULT_TROUBLESHOOTING
    
    def match_symptom(
        self, 
        appliance_type: str, 
        user_description: str
    ) -> Tuple[Optional[str], float]:
        """
        Match user's description to a known symptom.
        
        Returns:
            Tuple of (matched_symptom, confidence_score)
        """
        symptoms = self.get_common_symptoms(appliance_type)
        if not symptoms:
            return None, 0.0
        
        user_description = user_description.lower()
        
        # Simple keyword matching
        best_match = None
        best_score = 0.0
        
        for symptom in symptoms:
            symptom_words = set(symptom.lower().split())
            description_words = set(user_description.split())
            
            # Calculate overlap
            overlap = len(symptom_words & description_words)
            if overlap > 0:
                score = overlap / len(symptom_words)
                if score > best_score:
                    best_score = score
                    best_match = symptom
        
        return best_match, best_score
    
    def should_schedule_technician(
        self,
        troubleshooting_attempted: List[str],
        issue_resolved: bool,
        symptom_severity: str = "medium"  # "low", "medium", "high"
    ) -> bool:
        """
        Determine if a technician visit should be recommended.
        """
        if issue_resolved:
            return False
        
        # If high severity, recommend technician immediately
        if symptom_severity == "high":
            return True
        
        # If multiple troubleshooting steps tried without resolution
        if len(troubleshooting_attempted) >= 2 and not issue_resolved:
            return True
        
        return False
    
    def generate_diagnostic_summary(
        self,
        appliance_type: str,
        symptoms: List[str],
        troubleshooting_tried: List[str],
        troubleshooting_results: Dict[str, str]
    ) -> str:
        """Generate a summary of the diagnostic session for the technician."""
        summary_parts = [
            f"Appliance: {appliance_type.replace('_', ' ').title()}",
            f"\nReported Symptoms:",
        ]
        
        for symptom in symptoms:
            summary_parts.append(f"  - {symptom}")
        
        if troubleshooting_tried:
            summary_parts.append(f"\nTroubleshooting Steps Attempted:")
            for step in troubleshooting_tried:
                result = troubleshooting_results.get(step, "Unknown result")
                summary_parts.append(f"  - {step}: {result}")
        
        return "\n".join(summary_parts)
