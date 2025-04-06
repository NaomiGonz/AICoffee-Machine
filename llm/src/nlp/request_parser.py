import re
from typing import Dict, List, Any, Optional

class CoffeeRequestParser:
    """
    Enhanced parser for natural language coffee requests with more nuanced interpretation.
    """
    # Predefined dictionaries for request parsing
    COFFEE_TYPES = {
        'espresso': ['espresso', 'shot', 'single shot', 'double shot'],
        'americano': ['americano', 'american', 'long black'],
        'latte': ['latte', 'café latte'],
        'cappuccino': ['cappuccino', 'cap'],
        'pour_over': ['pour over', 'pourover', 'hand brew', 'manual brew', 'filter'],
        'french_press': ['french press', 'press pot', 'coffee press'],
        'cold_brew': ['cold brew', 'cold coffee'],
        'drip': ['drip coffee', 'regular coffee', 'standard coffee']
    }

    # Enhanced flavor keyword mapping with more specific descriptors
    FLAVOR_KEYWORDS = {
        'chocolate': ['chocolate', 'cocoa', 'dark chocolate', 'mocha', 'fudge', 'brownie'],
        'caramel': ['caramel', 'butterscotch', 'toffee', 'honey'],
        'fruity': ['fruity', 'berry', 'citrus', 'bright', 'zesty', 'lemon', 'orange', 'cherry', 'apple'],
        'nutty': ['nutty', 'almond', 'hazelnut', 'walnut', 'pecan'],
        'floral': ['floral', 'jasmine', 'lavender', 'rose'],
        'smooth': ['smooth', 'mild', 'gentle', 'velvety', 'silky'],
        'bold': ['bold', 'strong', 'intense'],
        'earthy': ['earthy', 'herbal', 'robust', 'woody']
    }

    # Body descriptors separate from size
    BODY_DESCRIPTORS = {
        'light': ['light', 'delicate', 'subtle'],
        'medium': ['medium', 'balanced', 'medium-bodied'],
        'full': ['full', 'rich', 'heavy', 'bold']
    }

    # Origin mapping for more precise flavor associations
    ORIGIN_FLAVOR_MAP = {
        'guatemala': {
            'primary_flavors': ['chocolate', 'caramel'],
            'roast_preference': 'medium',
            'brewing_hints': ['pour_over', 'drip']
        }
    }

    def parse_coffee_request(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language coffee request with enhanced precision.
        """
        normalized_request = request.lower().strip()
        
        parsed_request = {
            'original_request': request,
            'coffee_type': self._detect_coffee_type(normalized_request),
            'flavor_notes': self._extract_precise_flavor_notes(normalized_request),
            'body': self._detect_coffee_body(normalized_request),
            'origin': self._detect_origin(normalized_request),
            'roast_level': self._detect_roast_level(normalized_request),
            'serving_size': self._extract_serving_size(normalized_request),
            'brewing_context': self._extract_brewing_context(normalized_request)
        }
        
        # Refine coffee type based on context if not explicitly specified
        if parsed_request['coffee_type'] is None:
            parsed_request['coffee_type'] = self._infer_brew_method(parsed_request)
        
        return parsed_request

    def _detect_coffee_type(self, request: str) -> Optional[str]:
        """
        Detect coffee type only if explicitly mentioned.
        Returns None if no specific method is identified.
        """
        for coffee_type, keywords in self.COFFEE_TYPES.items():
            if any(keyword in request for keyword in keywords):
                return coffee_type
        return None

    def _extract_precise_flavor_notes(self, request: str) -> List[str]:
        """
        Advanced flavor extraction with priority on specific descriptors.
        """
        flavor_notes = []
        
        # Prioritize exact, specific flavor matches
        for flavor, keywords in self.FLAVOR_KEYWORDS.items():
            for keyword in keywords:
                if keyword in request:
                    flavor_notes.append(flavor)
                    break
        
        return flavor_notes

    def _detect_coffee_body(self, request: str) -> Optional[str]:
        """
        Detect coffee body separately from size or brewing method.
        """
        for body, descriptors in self.BODY_DESCRIPTORS.items():
            if any(desc in request for desc in descriptors):
                return body
        return None

    def _detect_origin(self, request: str) -> Optional[str]:
        """
        Detect specific coffee origin with more precise matching.
        """
        origins = {
            'Guatemala': ['guatemalan', 'guatemala'],
            'Ethiopia': ['ethiopian', 'ethiopia'],
            'Colombia': ['colombian', 'colombia']
        }
        
        for origin, keywords in origins.items():
            if any(keyword in request for keyword in keywords):
                return origin
        
        return None

    def _detect_roast_level(self, request: str) -> Optional[str]:
        """
        Detect the roast level of the coffee.
        
        Args:
            request (str): Normalized request
        
        Returns:
            Optional[str]: Detected roast level
        """
        # Handle case where request might be None
        if request is None:
            return None

        roast_levels = {
            'light': ['light', 'blonde', 'bright', 'mild', 'light roast'],
            'medium': ['medium', 'balanced', 'middle', 'medium roast'],
            'dark': ['dark', 'bold', 'intense', 'strong', 'french', 'italian', 'dark roast']
        }
        
        # Ensure request is converted to lowercase string
        request_lower = str(request).lower().strip()
        
        for roast, keywords in roast_levels.items():
            if any(keyword in request_lower for keyword in keywords):
                return roast
        
        return None

    def _extract_serving_size(self, request: str) -> Optional[float]:
        """
        Extract serving size only if explicitly mentioned.
        Supports fluid ounce specifications.
        """
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:oz|ounces?)', request)
        if amount_match:
            return float(amount_match.group(1))
        return None

    def _extract_brewing_context(self, request: str) -> Dict[str, Any]:
        """
        Extract contextual information about the brewing situation.
        """
        context = {}
        
        # Mood and time-based context
        mood_indicators = {
            'relaxed': ['relaxing', 'calm', 'afternoon', 'unwind'],
            'energetic': ['morning', 'wake up', 'boost']
        }
        
        for mood, indicators in mood_indicators.items():
            if any(indicator in request for indicator in indicators):
                context['mood'] = mood
                break
        
        return context

    def _infer_brew_method(self, parsed_request: Dict[str, Any]) -> Optional[str]:
        """
        Intelligently infer brew method based on context and flavor profile.
        
        Args:
            parsed_request (Dict[str, Any]): Parsed request details
        
        Returns:
            Optional[str]: Inferred brew method
        """
        # Extract flavor notes and context safely
        flavor_notes = parsed_request.get('flavor_notes', [])
        context = parsed_request.get('brewing_context', {})
        body = parsed_request.get('body')

        # Brew method inference based on flavor profile
        flavor_method_map = {
            'fruity': 'pour_over',
            'floral': 'pour_over',
            'bright': 'pour_over',
            'chocolate': 'french_press',
            'nutty': 'drip',
            'smooth': 'drip',
            'bold': 'espresso'
        }

        # First, check flavor notes for brew method
        for flavor in flavor_notes:
            if flavor in flavor_method_map:
                return flavor_method_map[flavor]

        # Check body type
        if body == 'light':
            return 'pour_over'
        elif body == 'full':
            return 'french_press'

        # Context-based inference
        if context.get('mood') == 'relaxed':
            return 'pour_over'

        # Default to drip coffee if no strong inference
        return 'drip'

def main():
    parser = CoffeeRequestParser()
    
    test_requests = [
        "A medium-bodied Guatemalan coffee with chocolate and caramel notes, perfect for a relaxing afternoon",
        "I want a fruity espresso with bright notes",
        "Something smooth and mellow",
        "Ethiopian pour-over with floral notes"
    ]
    
    for request in test_requests:
        print(f"\nRequest: {request}")
        parsed_request = parser.parse_coffee_request(request)
        import json
        print(json.dumps(parsed_request, indent=2))

if __name__ == "__main__":
    main()