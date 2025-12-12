# DigitalOcean Gradient AI Platform Integration

## Overview

BabbleBeaver now supports [DigitalOcean Gradient AI Platform](https://www.digitalocean.com/products/gen-ai-platform) as an additional AI provider option. This integration provides access to hosted AI models with optional knowledge bases for retrieval-augmented generation (RAG).

## Features

- **Hosted AI Models**: Access Llama, Mistral, and partner models (GPT, Claude) through DigitalOcean's infrastructure
- **Knowledge Bases**: Optional RAG capabilities with vector embeddings stored in managed OpenSearch
- **Flexible Priority System**: Use as primary, fallback, or backup provider
- **Cost-Effective**: Competitive pricing starting at $0.40/1M tokens for hosted models
- **Enterprise Ready**: Managed infrastructure with automatic scaling

## Setup

### 1. Create a DigitalOcean Agent

1. Sign up at [DigitalOcean](https://cloud.digitalocean.com)
2. Navigate to **Gradient AI Platform** → **Agents**
3. Click **Create Agent**
4. Configure your agent:
   - Select a model (e.g., Llama 3.1 70B, Mistral 7B)
   - Add instructions/system prompt (optional)
   - Attach knowledge bases if needed (optional)
5. Copy the **Agent URL** (format: `https://[agent-id].agents.do-ai.run`)
6. Generate an **API Token** from your account settings

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# DigitalOcean Gradient AI Platform
DIGITALOCEAN_AGENT_ENABLED=true
DIGITALOCEAN_API_TOKEN=your-api-token-here
DIGITALOCEAN_AGENT_URL=https://[agent-id].agents.do-ai.run
DIGITALOCEAN_PRIORITY=2
```

**Configuration Options:**

- `DIGITALOCEAN_AGENT_ENABLED`: Set to `true` to enable (default: `false`)
- `DIGITALOCEAN_API_TOKEN`: Your DigitalOcean API token (**required**)
- `DIGITALOCEAN_AGENT_URL`: Your agent's endpoint URL (**required**)
- `DIGITALOCEAN_PRIORITY`: Priority level (0=highest, default: 2)

### 3. Priority System

BabbleBeaver tries providers in order of priority (lowest number first):

```env
# Example multi-provider setup
GEMINI_PRIORITY=0          # Try Gemini first
OPENAI_PRIORITY=1          # Try OpenAI second
DIGITALOCEAN_PRIORITY=2    # Try DigitalOcean third
```

## Usage

### Basic Chat

Once configured, the DigitalOcean agent is automatically available as a fallback option:

```bash
curl -X POST http://localhost:8004/chatbot \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "prompt": "What is Buildly Labs?",
    "session_id": "user-123"
  }'
```

### Context-Aware Chat

Include optional context for more relevant responses:

```bash
curl -X POST http://localhost:8004/chatbot \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "prompt": "How do I create a new feature?",
    "session_id": "user-123",
    "context": {
      "product_name": "MyApp",
      "user_role": "developer",
      "current_page": "features"
    }
  }'
```

### Test Connection

Test your DigitalOcean agent connection:

```python
from modules.digitalocean import test_connection
import asyncio

result = asyncio.run(test_connection())
print(result)
```

Expected output:
```python
{
    'status': 'success',
    'message': 'Connection successful',
    'enabled': True,
    'configured': True,
    'response_time': 0.85,
    'sample_response': 'Hello! I am working correctly...'
}
```

## Pricing

### Model Costs (December 2024)

| Model | Input Cost | Output Cost | Total per 1M tokens |
|-------|------------|-------------|---------------------|
| **Hosted Models** | | | |
| Llama 3.1 70B | $0.80/1M | $0.80/1M | $0.80/1M |
| Mistral 7B | $0.40/1M | $0.40/1M | $0.40/1M |
| **Partner Models** | | | |
| GPT-4o (via DO) | ~$2.75/1M | ~$11.00/1M | Pass-through + 10% |
| Claude 3.5 Sonnet | ~$3.30/1M | ~$16.50/1M | Pass-through + 10% |

### Infrastructure Costs

If using knowledge bases (optional):

| Component | Cost Range | Description |
|-----------|-----------|-------------|
| OpenSearch DB | $20-200/month | Stores vector embeddings |
| Knowledge Base Indexing | $0.09/1M tokens | One-time indexing cost |
| Auto-Indexing | $0.09/1M tokens | Charged only when content changes |

### Monthly Cost Examples

**Simple Chat (250 tokens/request, 1,000 requests/day)**

| Provider | Model | Monthly Cost | Notes |
|----------|-------|--------------|-------|
| DigitalOcean | Llama 3.1 70B | $106 | Includes $100/month OpenSearch (optional) |
| Gemini | Flash 2.0 | $3.38 | Serverless, no infrastructure |
| OpenAI | GPT-4o-mini | $5.40 | Fully managed |

**Context-Aware Chat (1,100 tokens/request, 1,000 requests/day)**

| Provider | Model | Monthly Cost | Notes |
|----------|-------|--------------|-------|
| DigitalOcean | Llama 3.1 70B | $126 | Includes infrastructure |
| Gemini | Flash 2.0 | $14.85 | Serverless |
| OpenAI | GPT-4o-mini | $23.76 | Fully managed |

**Agent with Tools (1,700 tokens/request, 1,000 requests/day)**

| Provider | Model | Monthly Cost | Notes |
|----------|-------|--------------|-------|
| DigitalOcean | Llama 3.1 70B | $141 | Best for RAG use cases |
| Gemini | Flash 2.0 | $22.95 | Good for tool calling |
| OpenAI | GPT-4o-mini | $36.72 | Premium features |

### Cost Estimation API

Get real-time cost estimates:

```bash
# Compare all providers for a specific workflow
curl http://localhost:8004/api/cost-estimate?workflow=context_aware&requests_per_day=1000

# Get estimate for specific provider
curl http://localhost:8004/api/cost-estimate/digitalocean/llama_3_1_70b?requests_per_day=1000
```

## Knowledge Bases (Optional)

### When to Use

Knowledge bases are ideal for:
- **Domain-specific AI**: Company docs, technical manuals, product catalogs
- **RAG Applications**: Retrieve relevant context from large document sets
- **Compliance**: Keep sensitive data in your own infrastructure
- **Dynamic Content**: Auto-update with scheduled indexing

### Setup

1. **Create Knowledge Base** in DigitalOcean control panel
2. **Upload Data Sources**:
   - Direct file upload (.pdf, .txt, .md, .json, etc.)
   - DigitalOcean Spaces buckets
   - Web crawling (sitemap or seed URL)
   - Amazon S3, Dropbox
3. **Select Embedding Model**:
   - `text-embedding-ada-002` (OpenAI)
   - `text-embedding-3-small` (OpenAI)
   - Voyage embeddings
4. **Choose or Create OpenSearch DB**
5. **Wait for Indexing** (5-15 minutes for typical datasets)
6. **Attach to Agent**

### Auto-Indexing

Keep your knowledge base up-to-date:

```bash
# Schedule via DigitalOcean control panel
# Data sources → Schedule Indexing
# - Choose days and time (UTC)
# - Only charged when content changes
```

### Cost Optimization

- **Organize Files**: Use dedicated Spaces buckets with only relevant files
- **Limit Sources**: Use 5 or fewer buckets for optimal performance
- **Batch Uploads**: Upload <100 files at a time, each <2GB
- **Monitor Activity**: Download CSV logs before destroying knowledge bases

## API Reference

### DigitalOceanAgent Class

```python
from modules.digitalocean import DigitalOceanAgent

agent = DigitalOceanAgent(
    api_token="your-token",
    agent_url="https://[agent-id].agents.do-ai.run",
    timeout=30.0
)

# Chat completion
response = await agent.chat_completion(
    prompt="Tell me about Buildly",
    context={"product": "BabbleBeaver"},
    stream=False
)

# Cost estimate
cost = agent.get_cost_estimate(
    input_tokens=500,
    output_tokens=300
)

# Monthly estimate
monthly = agent.estimate_monthly_cost(
    requests_per_day=1000,
    avg_input_tokens=500,
    avg_output_tokens=300
)
```

### Cost Estimator

```python
from cost_estimator import CostEstimator, WorkflowType

# Single request cost
cost = CostEstimator.calculate_cost(
    provider='digitalocean',
    model='llama_3_1_70b',
    input_tokens=500,
    output_tokens=300
)

# Workflow estimate
estimate = CostEstimator.estimate_workflow_cost(
    provider='digitalocean',
    model='llama_3_1_70b',
    workflow_type=WorkflowType.CONTEXT_AWARE
)

# Monthly estimate
monthly = CostEstimator.estimate_monthly_cost(
    provider='digitalocean',
    model='llama_3_1_70b',
    requests_per_day=1000,
    workflow_type=WorkflowType.SIMPLE_CHAT,
    include_infrastructure=True
)

# Compare providers
comparison = CostEstimator.compare_providers(
    workflow_type=WorkflowType.CONTEXT_AWARE,
    requests_per_day=1000
)
```

## Troubleshooting

### Agent Not Responding

**Check Configuration:**
```python
from modules.digitalocean import get_agent
import asyncio

agent = get_agent()
print(f"Enabled: {agent.enabled}")
print(f"URL: {agent.agent_url}")
print(f"Has Token: {bool(agent.api_token)}")

# Test connection
result = asyncio.run(test_connection())
print(result)
```

**Common Issues:**

1. **401 Unauthorized**
   - Verify API token is correct
   - Check token hasn't expired
   - Ensure token has agent access permissions

2. **404 Not Found**
   - Verify agent URL format: `https://[agent-id].agents.do-ai.run`
   - Check agent still exists in DigitalOcean control panel
   - Ensure agent is deployed (not in draft state)

3. **Timeout**
   - Increase timeout: `DIGITALOCEAN_TIMEOUT=60`
   - Check agent is running (not stopped)
   - Verify network connectivity

4. **Empty Response**
   - Check agent logs in DigitalOcean control panel
   - Verify agent has a model configured
   - Try simpler prompts to test

### Knowledge Base Issues

1. **Indexing Failed**
   - Download activity logs (CSV) from Activity tab
   - Check file formats are supported
   - Verify files are under 2GB
   - Ensure OpenSearch DB has enough capacity

2. **Irrelevant Results**
   - Review agent instructions/system prompt
   - Check knowledge base contains relevant docs
   - Try more specific queries
   - Consider adjusting embedding model

3. **Slow Indexing**
   - Upload fewer files per batch (<100)
   - Use dedicated Spaces buckets
   - Check file sizes (larger = slower)
   - Monitor OpenSearch DB performance

## Best Practices

### When to Use DigitalOcean

✅ **Good For:**
- RAG applications with custom knowledge bases
- Cost-sensitive production workloads
- Compliance requirements (data stays in your infrastructure)
- Long-running agent workflows
- Testing multiple models (hosted + partner)

❌ **Consider Alternatives For:**
- Ultra-low latency requirements (<500ms)
- Serverless/pay-per-use only (OpenSearch DB has fixed cost)
- No RAG needed and using latest models (Gemini 2.0 Flash cheaper)

### Cost Optimization

1. **Right-Size OpenSearch**: Start with smallest DB, scale up if needed
2. **Disable Knowledge Bases**: If not using RAG, skip OpenSearch entirely
3. **Use Hosted Models**: Llama/Mistral much cheaper than partner models
4. **Monitor Usage**: Check cost estimates regularly
5. **Auto-Indexing**: Only enable if content changes frequently

### Security

1. **Protect API Tokens**: Never commit to git, use env variables
2. **Rotate Tokens**: Generate new tokens periodically
3. **Scope Permissions**: Use agent-specific tokens when possible
4. **Monitor Logs**: Review agent traces in DigitalOcean console

## Resources

- [DigitalOcean Gradient AI Platform Docs](https://docs.digitalocean.com/products/gradient-ai-platform/)
- [Agent Creation Guide](https://docs.digitalocean.com/products/gradientai-platform/how-to/create-agents/)
- [Knowledge Base Guide](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-manage-agent-knowledge-bases/)
- [Pricing Details](https://docs.digitalocean.com/products/gradientai-platform/details/pricing/)
- [Available Models](https://docs.digitalocean.com/products/gradientai-platform/details/models/)
- [API Reference](https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform)

## Support

For BabbleBeaver integration issues:
- GitHub Issues: [buildly-labs/babblebeaver](https://github.com/buildly-labs/babblebeaver/issues)
- Check logs: `docker logs babblebeaver` or check application logs

For DigitalOcean platform issues:
- [DigitalOcean Support](https://docs.digitalocean.com/support/)
- [Community Forums](https://www.digitalocean.com/community/)

---

**Last Updated**: December 9, 2024  
**Version**: BabbleBeaver 1.0 with DigitalOcean Integration
