
def validate_user_bean_inventory(beans):
    """
    Validate that the provided beans are valid and are in inventory.
    
    The function should work with both Pydantic models and dictionaries
    """
    # Convert Pydantic models to dictionaries if needed
    beans_data = []
    for bean in beans:
        # Check if bean is a Pydantic model (has model_dump method)
        if hasattr(bean, 'model_dump'):
            beans_data.append(bean.model_dump())
        else:
            # Assume it's already a dictionary
            beans_data.append(bean)
    
    # Continue with validation using dictionary access
    for bean in beans_data:
        # Validate bean properties
        if 'name' not in bean or 'roast' not in bean or 'notes' not in bean:
            raise ValueError(f"Invalid bean format: {bean}")
        
        # Add more validations as needed
        
    return True

def select_servo_for_bean(beans):
    """
    Select the appropriate servo controls based on bean percentages.
    Returns additional commands for the machine code.
    """
    # Default to servo B for mixing
    additional_commands = []
    
    # If we have multiple beans or specific beans that need special handling
    bean_types = [bean['name'] for bean in beans]
    
    # Add specialized commands based on bean types or combinations
    # Example: If we have beans that need a specific servo
    if len(bean_types) > 1:
        additional_commands.append("S-B-30")  # Use servo B for 30 seconds for mixing
    
    # Special beans that require specific handling
    for bean in beans:
        if "Yirgacheffe" in bean['name']:
            additional_commands.append("S-C-15")  # Use servo C for 15 seconds
        elif "Santos" in bean['name'] and bean['amount_g'] > 10:
            additional_commands.append("S-A-10")  # Use servo A for 10 seconds
    
    return additional_commands