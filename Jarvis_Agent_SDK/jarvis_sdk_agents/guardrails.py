from agents import input_guardrail, GuardrailFunctionOutput, RunContextWrapper, Agent

@input_guardrail
async def validate_code_input(ctx: RunContextWrapper, agent: Agent, input_data: str):
    # Extract code and language from input (simplified for demonstration)
    # In a real implementation, you'd parse the input more robustly
    code = input_data if isinstance(input_data, str) else ""
    language = "python"  # Default to python
    
    if language not in ["python", "javascript", "java", "c++"]:
        return GuardrailFunctionOutput(
            output_info={"error": "Unsupported language"},
            tripwire_triggered=True
        )
    if len(code) > 2000:
        return GuardrailFunctionOutput(
            output_info={"error": "Code too long"}, 
            tripwire_triggered=True
        )
    
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=False
    )

@input_guardrail
async def validate_review_input(ctx: RunContextWrapper, agent: Agent, input_data: str):
    # Extract code and review_type from input (simplified for demonstration)
    # In a real implementation, you'd parse the input more robustly
    code = input_data if isinstance(input_data, str) else ""
    review_type = "security"  # Default to security
    
    if review_type not in ["security", "performance", "style", "architecture"]:
        return GuardrailFunctionOutput(
            output_info={"error": "Invalid review type"},
            tripwire_triggered=True
        )
    if len(code) > 5000:
        return GuardrailFunctionOutput(
            output_info={"error": "Code too long for review"},
            tripwire_triggered=True
        )
    
    return GuardrailFunctionOutput(
        output_info={"valid": True},
        tripwire_triggered=False
    ) 