import torch
import re
import json
from transformers import (
    pipeline, 
    AutoTokenizer, 
    AutoModelForCausalLM
)
from typing import Dict, Any, Optional, List

class LLMHandler:
    """
    Handles interaction with EleutherAI's GPT-Neo model 
    for coffee brewing recommendations.
    """
    
    def __init__(
        self, 
        model_name: str = "EleutherAI/gpt-neo-1.3B",
        device: Optional[str] = None
    ):
        """
        Initialize the LLM handler with GPT-Neo model.
        
        Args:
            model_name (str): Hugging Face model identifier
            device (str, optional): Device to run the model on (cuda/cpu)
        """
        # Determine device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load tokenizer and model
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Add pad token if not exists
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto"
            )
            
            # Create generation pipeline
            self.pipe = pipeline(
                "text-generation", 
                model=self.model, 
                tokenizer=self.tokenizer,
                device=device
            )
        except Exception as e:
            print(f"Error loading model {model_name}: {e}")
            raise
    
    def _format_prompt(self, user_request: str) -> str:
        """
        Format the prompt for GPT-Neo model.
        
        Args:
            user_request (str): User's coffee request
        
        Returns:
            str: Formatted prompt
        """
        system_prompt = """You are an expert coffee brewing assistant. 
Help the user brew the perfect coffee by providing a detailed brewing recommendation in strict JSON format.

Example JSON Output:
{
  "coffee_type": "espresso",
  "beans": [
    {
      "name": "Ethiopian Yirgacheffe",
      "roast": "Light",
      "flavor_notes": ["fruity", "floral"],
      "amount_g": 18
    }
  ],
  "brewing_parameters": {
    "water_temperature_c": 94,
    "water_pressure_bar": 9,
    "extraction_time_sec": 28
  },
  "recommendations": {
    "flavor_notes": "Bright, fruity espresso",
    "brewing_tips": "Gentle extraction to highlight delicate flavors"
  }
}

User Request: {request}
JSON Output:""".format(request=user_request)
        
        return system_prompt
    
    def generate_coffee_recommendation(
        self, 
        user_request: str, 
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate a coffee brewing recommendation using GPT-Neo.
        
        Args:
            user_request (str): User's coffee request
            max_retries (int): Number of retry attempts for valid JSON
        
        Returns:
            Dict: Generated coffee brewing recommendation
        """
        # Format the prompt
        full_prompt = self._format_prompt(user_request)
        
        # Attempt to generate a valid recommendation
        for attempt in range(max_retries):
            try:
                # Generate response
                outputs = self.pipe(
                    full_prompt, 
                    max_length=500, 
                    num_return_sequences=1,
                    temperature=0.7
                )
                
                # Extract the generated text
                generated_text = outputs[0]['generated_text']
                
                # Extract JSON from the generated text
                json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    recommendation = json.loads(json_str)
                    return recommendation
            
            except (json.JSONDecodeError, AttributeError, IndexError) as e:
                print(f"JSON parsing error (attempt {attempt + 1}): {e}")
        
        # Fallback recommendation if all attempts fail
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
                "brewing_tips": "Default recommendation due to generation error"
            }
        }

# Example usage demonstration
def main():
    # Initialize LLM Handler
    try:
        llm_handler = LLMHandler()
        
        # Test coffee recommendation generation
        test_requests = [
            "I want a fruity espresso with bright notes",
            "Make me a large cappuccino with chocolatey flavor",
            "Can I have a pour-over with nutty profile?"
        ]
        
        for request in test_requests:
            print(f"\n--- Generating Recommendation for: {request} ---")
            recommendation = llm_handler.generate_coffee_recommendation(request)
            
            # Pretty print recommendation
            print(json.dumps(recommendation, indent=2))
    
    except Exception as e:
        print(f"Error initializing LLM: {e}")

if __name__ == "__main__":
    main()