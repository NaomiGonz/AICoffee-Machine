import json
import re
from typing import Dict, Any, Optional, List

class PromptGenerator:
    """
    Generates structured prompts for Large Language Models 
    to interpret coffee brewing requests.
    """
    
    @staticmethod
    def generate_system_prompt() -> str:
        """
        Generate a comprehensive system prompt for the coffee brewing assistant.
        
        Returns:
            str: Detailed system prompt for LLM
        """
        return """
You are an expert coffee brewing assistant with deep knowledge of coffee preparation, 
bean characteristics, and brewing techniques. Your goal is to help users brew the perfect 
cup of coffee tailored to their preferences.

Coffee Brewing Guidelines:
1. Understand the user's specific coffee request
2. Identify the desired coffee type and flavor profile
3. Select appropriate beans and brewing method
4. Provide precise brewing parameters
5. Offer personalized brewing recommendations

Brewing Parameter Considerations:
- Match bean origins to flavor notes
- Adjust water temperature based on roast level
- Consider brewing method (espresso, pour-over, etc.)
- Optimize extraction for desired flavor profile

Flavor Profile Mapping:
- Light Roasts: Typically fruity, floral, bright
  * Higher brewing temperatures (94-96°C)
  * Emphasize delicate, complex flavors
- Medium Roasts: Balanced, smooth
  * Moderate brewing temperatures (92-94°C)
  * Highlight balanced flavor characteristics
- Dark Roasts: Bold, rich, chocolatey
  * Lower brewing temperatures (88-91°C)
  * Minimize bitter notes

Recommended Output Format:
{
  "coffee_type": "espresso|americano|pour_over|etc.",
  "beans": [
    {
      "name": "Bean Origin/Name",
      "roast": "Light/Medium/Dark",
      "flavor_notes": ["flavor1", "flavor2"],
      "amount_g": 0-20
    }
  ],
  "brewing_parameters": {
    "water_temperature_c": 88-96,
    "water_pressure_bar": 1-9,
    "extraction_time_sec": 25-30
  },
  "recommendations": {
    "flavor_notes": "Descriptive flavor profile",
    "brewing_tips": "Additional personalized advice"
  }
}

Always prioritize the user's stated preferences while applying expert coffee knowledge.
Provide clear, actionable brewing guidance.
"""
    
    @classmethod
    def generate_user_prompt(
        cls, 
        parsed_request: Dict[str, Any]
    ) -> str:
        """
        Generate a specific user prompt based on parsed request.
        
        Args:
            parsed_request (Dict): Parsed coffee request details
        
        Returns:
            str: Formatted prompt for LLM
        """
        # Prepare context for LLM
        prompt_context = {
            "original_request": parsed_request.get('original_request', ''),
            "coffee_type": parsed_request.get('coffee_type', 'espresso'),
            "flavor_notes": parsed_request.get('flavor_notes', []),
            "size": parsed_request.get('size'),
            "roast_level": parsed_request.get('roast_level'),
            "additional_preferences": parsed_request.get('additional_preferences', {})
        }
        
        # Construct detailed prompt
        prompt_lines = [
            f"User's Original Request: {prompt_context['original_request']}",
            "",
            "Please help me brew a coffee with the following characteristics:"
        ]
        
        # Add specific details to prompt
        if prompt_context['coffee_type']:
            prompt_lines.append(f"- Coffee Type: {prompt_context['coffee_type']}")
        
        if prompt_context['flavor_notes']:
            prompt_lines.append(f"- Desired Flavor Notes: {', '.join(prompt_context['flavor_notes'])}")
        
        if prompt_context['size']:
            prompt_lines.append(f"- Preferred Size: {prompt_context['size']}")
        
        if prompt_context['roast_level']:
            prompt_lines.append(f"- Roast Level: {prompt_context['roast_level']}")
        
        # Add additional preferences
        if prompt_context['additional_preferences']:
            prompt_lines.append("Additional Preferences:")
            for pref, value in prompt_context['additional_preferences'].items():
                prompt_lines.append(f"- {pref.capitalize()}: {value}")
        
        prompt_lines.extend([
            "",
            "Provide a detailed brewing recommendation following the output format in the system prompt."
        ])
        
        return "\n".join(prompt_lines)
    
    @staticmethod
    def parse_llm_response(
        llm_response: str, 
        default_fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse the LLM's response and extract structured brewing information.
        
        Args:
            llm_response (str): Raw response from the LLM
            default_fallback (Dict, optional): Fallback recommendation
        
        Returns:
            Dict: Parsed and structured brewing recommendation
        """
        # Attempt to extract JSON from response
        try:
            # Look for JSON within code blocks or standalone
            json_match = re.search(r'```json\n(.*?)```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON in the entire response
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                json_str = json_match.group(0) if json_match else llm_response
            
            # Parse JSON
            parsed_recommendation = json.loads(json_str)
            return parsed_recommendation
        
        except (json.JSONDecodeError, AttributeError):
            # Fallback to default recommendation if parsing fails
            if default_fallback:
                return default_fallback
            
            # Generic fallback recommendation
            return {
                "coffee_type": "espresso",
                "beans": [{
                    "name": "House Blend",
                    "roast": "Medium",
                    "flavor_notes": ["balanced"],
                    "amount_g": 18
                }],
                "brewing_parameters": {
                    "water_temperature_c": 92,
                    "water_pressure_bar": 9,
                    "extraction_time_sec": 28
                },
                "recommendations": {
                    "flavor_notes": "Balanced, smooth coffee",
                    "brewing_tips": "Default recommendation due to parsing error"
                }
            }

# Example usage demonstration
def main():
    # Initialize PromptGenerator
    prompt_generator = PromptGenerator()
    
    # Print system prompt
    print("SYSTEM PROMPT:")
    print(prompt_generator.generate_system_prompt())
    
    # Test request parsing
    test_requests = [
        {
            "original_request": "I want a fruity espresso with bright notes",
            "coffee_type": "espresso",
            "flavor_notes": ["fruity"],
            "additional_preferences": {}
        },
        {
            "original_request": "Make me a large cappuccino with chocolatey flavor and oat milk",
            "coffee_type": "cappuccino",
            "flavor_notes": ["chocolatey"],
            "size": "large",
            "additional_preferences": {"milk": "oat"}
        }
    ]
    
    # Demonstrate prompt generation and parsing
    for request in test_requests:
        print("\n--- Request Processing ---")
        print(f"Original Request: {request['original_request']}")
        
        # Generate user prompt
        user_prompt = prompt_generator.generate_user_prompt(request)
        print("\nGenerated User Prompt:")
        print(user_prompt)
        
        # Simulate LLM response (in a real scenario, this would be an actual LLM call)
        simulated_llm_response = json.dumps({
            "coffee_type": request['coffee_type'],
            "beans": [{
                "name": "Ethiopian Yirgacheffe" if "fruity" in request.get('flavor_notes', []) 
                       else "Brazilian Santos",
                "roast": "Light" if "fruity" in request.get('flavor_notes', []) else "Medium",
                "flavor_notes": request.get('flavor_notes', ['balanced']),
                "amount_g": 18
            }],
            "brewing_parameters": {
                "water_temperature_c": 94 if "fruity" in request.get('flavor_notes', []) else 92,
                "water_pressure_bar": 9,
                "extraction_time_sec": 28
            },
            "recommendations": {
                "flavor_notes": f"Emphasizing {', '.join(request.get('flavor_notes', ['balanced']))} profile",
                "brewing_tips": f"Prepared as {'large' if request.get('size') else 'standard'} {request['coffee_type']}"
            }
        }, indent=2)
        
        # Parse simulated LLM response
        parsed_response = prompt_generator.parse_llm_response(simulated_llm_response)
        
        print("\nParsed LLM Response:")
        print(json.dumps(parsed_response, indent=2))

if __name__ == "__main__":
    main()