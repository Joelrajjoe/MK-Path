# AI Structured Output Schemas

All AI model interactions must return structured JSON that complies with the schemas outlined below. Output must be strictly validated before database persistence.

---

## 1. Concept Extraction Schema

Invoked upon PDF text ingestion to extract key educational concepts and their relationships.

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "OBJECT",
  "properties": {
    "concepts": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": { "type": "STRING" },
          "description": { "type": "STRING" },
          "exam_relevance": { "type": "INTEGER", "minimum": 0, "maximum": 100 },
          "industry_relevance": { "type": "INTEGER", "minimum": 0, "maximum": 100 },
          "difficulty": { "type": "STRING", "enum": ["basic", "intermediate", "advanced"] },
          "prerequisites": {
            "type": "ARRAY",
            "items": { "type": "STRING" }
          }
        },
        "required": ["name", "description", "exam_relevance", "industry_relevance", "difficulty", "prerequisites"]
      }
    },
    "relationships": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "source": { "type": "STRING" },
          "target": { "type": "STRING" },
          "relationship_type": { "type": "STRING" }
        },
        "required": ["source", "target", "relationship_type"]
      }
    }
  },
  "required": ["concepts", "relationships"]
}
```

---

## 2. Assessment Question Generation Schema

Invoked dynamically to generate multiple-choice questions for specific concepts.

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "OBJECT",
  "properties": {
    "questions": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "question_text": { "type": "STRING" },
          "options": {
            "type": "ARRAY",
            "items": { "type": "STRING" },
            "minItems": 4,
            "maxItems": 4
          },
          "correct_option_index": { "type": "INTEGER", "minimum": 0, "maximum": 3 },
          "difficulty": { "type": "STRING", "enum": ["basic", "intermediate", "advanced"] },
          "explanation": { "type": "STRING" }
        },
        "required": ["question_text", "options", "correct_option_index", "difficulty", "explanation"]
      }
    }
  },
  "required": ["questions"]
}
```