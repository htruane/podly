# Model Pricing Configuration

Custom pricing configuration for LLM models not included in LiteLLM's default pricing database.

## Configuration File

Model pricing is configured in `src/model_pricing.csv`:

```csv
model_pattern,input_cost_per_million,output_cost_per_million
glm-4.5-air,0.2,1.1
glm-4-5-air,0.2,1.1
glm-4.6,0.6,2.2
glm-4-6,0.6,2.2
```

## Format

- `model_pattern`: Case-insensitive pattern to match against model names
- `input_cost_per_million`: Cost per 1 million input tokens in USD
- `output_cost_per_million`: Cost per 1 million output tokens in USD

## Pattern Matching

The system performs case-insensitive substring matching. For example:
- Pattern `glm-4.5-air` matches: `glm-4.5-air`, `GLM-4.5-AIR`, `zhipu/glm-4.5-air`
- Pattern `glm-4.6` matches: `glm-4.6`, `GLM-4.6`, `zhipu/glm-4.6`

## Adding New Models

To add pricing for a new model:

1. Edit `src/model_pricing.csv`
2. Add a new row with the model pattern and costs
3. Restart the application to reload the configuration

Example:
```csv
my-custom-model,0.5,1.5
```

## Updating Existing Pricing

When model pricing changes:

1. Update the costs in `src/model_pricing.csv`
2. Restart the application

No code changes are required.

## Implementation

Pricing is loaded from CSV at application startup by `ModelPricingConfig` class in [src/podcast_processor/model_pricing.py](src/podcast_processor/model_pricing.py). The pricing is applied during LLM API calls in [src/podcast_processor/ad_classifier.py](src/podcast_processor/ad_classifier.py).
