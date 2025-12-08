# BabbleBeaver Context-Aware System Configuration

## Overview

BabbleBeaver includes a **context-aware system** that automatically incorporates user context, product data, and session information into AI responses. This makes conversations more relevant and personalized without manual intervention.

## How It Works

### 1. Context Sources

BabbleBeaver accepts context from multiple sources:
- **Product Context**: `product_uuid`, product information
- **User Context**: User ID, preferences, role
- **Page Context**: Current page, workflow step, form data
- **Session Context**: Conversation history, previous interactions
- **Custom Context**: Any additional key-value pairs

### 2. System Prompt Enhancement

The system automatically enhances the AI's system prompt with available context:

```python
# Example: Frontend sends context
{
  "message": "What should I rename this to?",
  "context": {
    "product_uuid": "abc-123",
    "product_name": "My Product",
    "current_page": "product_settings",
    "user_role": "product_owner"
  }
}

# BabbleBeaver automatically adds to system prompt:
"CURRENT CONTEXT:
- User is viewing: product_settings
- Current product: My Product (UUID: abc-123)
- User role: product_owner

Use this context to provide relevant, specific answers."
```

### 3. Agentic Enrichment

When enabled, the Buildly Agent automatically:
- Detects product UUIDs
- Fetches real-time product data
- Enriches context with features, releases, etc.
- No manual configuration needed

## Configuration

### Basic Setup (context-aware-config.json)

```json
{
  "context_mode": "auto",
  "context_sources": {
    "product_context": {
      "enabled": true,
      "auto_fetch": true,
      "fields": ["product_uuid", "product_name", "product_type"]
    },
    "user_context": {
      "enabled": true,
      "fields": ["user_id", "user_role", "preferences"]
    },
    "page_context": {
      "enabled": true,
      "fields": ["current_page", "workflow_step", "form_data"]
    },
    "session_context": {
      "enabled": true,
      "include_history": true
    }
  },
  "system_prompt": {
    "template": "context_aware",
    "custom_instructions": ""
  }
}
```

### Environment Variables

```bash
# Enable context-aware mode
CONTEXT_AWARE_MODE=auto  # auto, manual, disabled

# Context enrichment
ENRICH_WITH_PRODUCT_DATA=true
ENRICH_WITH_USER_DATA=true
ENRICH_WITH_PAGE_DATA=true

# Custom system prompt template
CONTEXT_PROMPT_TEMPLATE=default  # default, minimal, verbose, custom
```

## Frontend Integration

### Sending Context

```javascript
// Example: Product settings page
const response = await fetch('/chatbot', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`
  },
  body: JSON.stringify({
    message: 'What should I rename this to?',
    context: {
      // Product context
      product_uuid: currentProduct.uuid,
      product_name: currentProduct.name,
      product_type: currentProduct.type,
      
      // Page context
      current_page: 'product_settings',
      workflow_step: 'naming',
      
      // User context
      user_role: currentUser.role,
      user_preferences: currentUser.preferences
    }
  })
});

// BabbleBeaver automatically understands:
// - User is renaming a product
// - Current product details
// - User's role and permissions
// - Page they're on
```

### React Hook Example

```javascript
import { useState, useContext } from 'react';
import { ProductContext, UserContext, PageContext } from './contexts';

function useBabbleBeaver() {
  const product = useContext(ProductContext);
  const user = useContext(UserContext);
  const page = useContext(PageContext);
  
  const sendMessage = async (message) => {
    const response = await fetch('/chatbot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
      },
      body: JSON.stringify({
        message,
        context: {
          // Automatically include context
          product_uuid: product?.uuid,
          product_name: product?.name,
          current_page: page?.name,
          user_role: user?.role
        }
      })
    });
    
    return response.json();
  };
  
  return { sendMessage };
}
```

## Use Cases

### 1. Product Management

```javascript
// User asks: "What should I name this feature?"
// Context automatically includes:
{
  message: "What should I name this feature?",
  context: {
    product_uuid: "abc-123",
    product_name: "Mobile App",
    current_feature: "user_authentication",
    existing_features: ["login", "signup", "password_reset"]
  }
}

// AI responds with context awareness:
// "Based on your Mobile App product, I suggest naming this feature 
// 'Secure Login' to align with your existing authentication features."
```

### 2. Technical Documentation

```javascript
// User asks: "Write a user story for this"
// Context includes:
{
  message: "Write a user story for this",
  context: {
    current_page: "feature_editor",
    feature_name: "Dark Mode",
    product_type: "web_app",
    target_audience: "designers"
  }
}

// AI responds contextually:
// "User Story: As a designer using the web app, I want to enable 
// dark mode so that I can reduce eye strain during long work sessions."
```

### 3. Release Planning

```javascript
// User asks: "What should be in the next release?"
// Context includes:
{
  message: "What should be in the next release?",
  context: {
    product_uuid: "abc-123",
    current_release: "v1.2.0",
    pending_features: ["feature-1", "feature-2", "feature-3"],
    blockers: ["bug-456"],
    timeline: "2_weeks"
  }
}

// AI responds with specific recommendations
```

## System Prompt Templates

### Default Template (Balanced)

```
You are an intelligent AI assistant with access to the following context:

CURRENT CONTEXT:
{context_summary}

Use this context to provide relevant, specific answers. Reference the context naturally in your responses.
```

### Minimal Template (Subtle)

```
{base_system_prompt}

Current Context: {context_summary}
```

### Verbose Template (Detailed)

```
You are a context-aware AI assistant. You have access to detailed information about the user's current situation.

PRODUCT CONTEXT:
{product_context}

USER CONTEXT:
{user_context}

PAGE CONTEXT:
{page_context}

INSTRUCTIONS:
1. Use the provided context to give specific, relevant answers
2. Reference context details when appropriate
3. If context is insufficient, ask clarifying questions
4. Maintain context awareness across the conversation
```

### Custom Template

Create your own in `context-prompt-templates.txt`:

```
{your_custom_template}

Available variables:
- {product_context}
- {user_context}
- {page_context}
- {session_context}
- {context_summary}
- {base_system_prompt}
```

## Multi-Use Case Adaptation

### Buildly Labs (Product Management)

```python
{
  "use_case": "buildly_labs",
  "context_fields": ["product_uuid", "feature_uuid", "release_uuid"],
  "system_prompt_additions": "Focus on product management, agile practices, and technical documentation."
}
```

### E-commerce (Shopping)

```python
{
  "use_case": "ecommerce",
  "context_fields": ["cart_id", "product_id", "category", "price_range"],
  "system_prompt_additions": "Focus on product recommendations, shopping assistance, and order support."
}
```

### Healthcare (Patient Support)

```python
{
  "use_case": "healthcare",
  "context_fields": ["patient_id", "appointment_type", "medical_history_summary"],
  "system_prompt_additions": "Focus on health information, appointment scheduling, and medical support."
}
```

### Education (Learning)

```python
{
  "use_case": "education",
  "context_fields": ["course_id", "student_level", "current_lesson"],
  "system_prompt_additions": "Focus on educational guidance, learning paths, and knowledge assessment."
}
```

## Benefits

### 1. **Automatic Context Awareness**
- No manual prompt engineering needed
- Context automatically included in every response
- Reduces "AI doesn't understand my situation" issues

### 2. **Adaptable to Any Use Case**
- Configure context fields per use case
- Custom system prompt templates
- Environment-specific configurations

### 3. **Improved Response Quality**
- More specific, relevant answers
- Reduces need for clarifying questions
- Better user experience

### 4. **Easy Frontend Integration**
- Just send context object with message
- Works with existing code
- Progressive enhancement (context optional)

### 5. **Privacy-Aware**
- Only send context you want to share
- No automatic data collection
- Full control over what's included

## Best Practices

### 1. **Send Relevant Context Only**
```javascript
// ❌ Too much context
context: {
  entire_user_object: {...},  // 50+ fields
  all_products: [...],         // Huge array
  full_database: {...}         // Overkill
}

// ✅ Relevant context only
context: {
  user_role: "product_owner",
  product_uuid: "abc-123",
  current_page: "settings"
}
```

### 2. **Structure Context Clearly**
```javascript
// ✅ Well-structured
context: {
  product: {
    uuid: "abc-123",
    name: "My Product"
  },
  user: {
    role: "owner",
    id: "user-456"
  },
  page: {
    name: "settings",
    section: "naming"
  }
}
```

### 3. **Update Context as User Navigates**
```javascript
// Update context when page changes
useEffect(() => {
  setPageContext({
    current_page: location.pathname,
    workflow_step: currentStep
  });
}, [location.pathname, currentStep]);
```

### 4. **Don't Duplicate Message in Context**
```javascript
// ❌ Redundant
{
  message: "What should I rename this to?",
  context: {
    user_question: "What should I rename this to?"  // Duplicate
  }
}

// ✅ Context provides additional info
{
  message: "What should I rename this to?",
  context: {
    current_name: "My Product",
    product_type: "mobile_app"
  }
}
```

## Testing

### Test Context Awareness

```bash
# Without context
curl -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"message":"What should I rename this to?"}'

# Response: "I'd need more information about what you're trying to rename..."

# With context
curl -X POST http://localhost:8004/chatbot \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "message":"What should I rename this to?",
    "context": {
      "product_name": "My Mobile App",
      "product_type": "ios_app",
      "current_page": "product_settings"
    }
  }'

# Response: "For your iOS mobile app 'My Mobile App', I suggest..."
```

---

**Status:** ✅ Ready to implement  
**Complexity:** Medium  
**Breaking Changes:** None (backward compatible)  
**Benefits:** High (better UX, more relevant responses)
