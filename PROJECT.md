# Production RAG Knowledge Assistant

## Purpose

Production RAG Knowledge Assistant is a local educational project that demonstrates how modern enterprise knowledge assistants are built using:

* LangGraph
* MCP (Model Context Protocol)
* LlamaIndex
* Qdrant
* Hybrid Retrieval
* Reranking
* OpenAI-compatible LLMs

The project is designed as a practical companion for a Production RAG lecture.

The goal is not to build a production-ready enterprise platform, but to demonstrate realistic architectural patterns commonly used in modern AI systems.

---

## Goals

The project should demonstrate:

* agent-based interaction with a knowledge base;
* MCP as a tool integration layer;
* document indexing workflows;
* human-in-the-loop approval flows;
* semantic search;
* keyword search;
* hybrid retrieval;
* reranking;
* source attribution;
* retrieval evaluation.

The system should be explainable and transparent.

Users must be able to understand where an answer came from and which documents were used.

---

## Non-Goals

The project does not aim to implement:

* multi-agent systems;
* distributed architecture;
* microservices;
* Kubernetes deployment;
* authentication and authorization;
* production monitoring;
* long-term memory;
* Langfuse;
* LLM-as-a-Judge evaluation;
* workflow automation;
* enterprise security controls.

The project intentionally focuses on a single knowledge assistant scenario.

---

## Problem Statement

Large Language Models cannot reliably answer questions about proprietary company information.

A knowledge assistant must retrieve relevant information from a document corpus before generating an answer.

Simple vector search is often insufficient for production environments.

Modern systems typically combine:

* semantic retrieval;
* keyword retrieval;
* reranking;
* source attribution.

This project demonstrates such an architecture.

---

## High-Level Architecture

```text
User
  ↓
CLI Chat
  ↓
LangGraph Agent
  ↓
MCP Client
  ↓
Knowledge MCP Server
  ↓
Retrieval Layer
  ↓
Qdrant
```

The agent never interacts with the vector database directly.

All knowledge access happens through MCP tools and resources.

---

## Main Components

### LangGraph Agent

The agent is responsible for:

* conversation handling;
* chat history management;
* tool selection;
* MCP communication;
* response generation.

The agent acts as the primary entry point for users.

---

### Knowledge MCP Server

The MCP server exposes knowledge-related capabilities.

Responsibilities:

* document indexing;
* document search;
* document retrieval;
* statistics;
* knowledge access.

The MCP server is the system boundary between the agent and the retrieval layer.

---

### Retrieval Layer

The retrieval layer implements a modern retrieval pipeline:

```text
Dense Search
      +
BM25 Search
      ↓
Fusion
      ↓
Reranker
      ↓
Top Context
```

The retrieval layer is responsible for finding the most relevant document fragments.

---

### Vector Database

Qdrant stores:

* dense vectors;
* sparse vectors;
* document metadata;
* chunk metadata.

The database acts as the retrieval backend.

---

### LLM Layer

The project uses an external OpenAI-compatible endpoint.

The LLM is responsible for:

* tool reasoning;
* answer generation;
* query rewriting;
* intent classification.

The project does not host the main LLM locally.

---

## Knowledge Base

The knowledge base consists of synthetic corporate documents generated using LLMs.

Examples:

* remote work policy;
* onboarding policy;
* travel policy;
* security policy;
* equipment policy;
* expense policy;
* incident response procedures.

Documents are intentionally large enough to demonstrate chunking and retrieval.

---

## User Flows

### Question Answering

```text
User Question
      ↓
Agent
      ↓
MCP Search
      ↓
Retrieval
      ↓
LLM
      ↓
Answer + Sources
```

---

### Document Indexing

```text
User Request
      ↓
Index Preview
      ↓
Human Approval
      ↓
Indexing
```

The system must require user confirmation before modifying the index.

---

### Retrieval Retry

When the user indicates that an answer did not solve the problem:

```text
User Feedback
      ↓
Query Rewrite
      ↓
New Retrieval
      ↓
New Answer
```

The agent uses conversation history to improve retrieval quality.

---

## Source Attribution

All answers must be grounded in retrieved content.

The system should display:

* document title;
* document path;
* section title;
* line range.

Example:

```text
Sources:

[1] Remote Work Policy
    File: docs/remote_work_policy.md
    Section: Work From Another Country
    Lines: 84-112
```

Users should always be able to inspect the origin of an answer.

---

## Technology Stack

### Agent Layer

* LangGraph

### MCP Layer

* Model Context Protocol (MCP)

### Document Processing

* LlamaIndex

### Embeddings

* BAAI/bge-m3

### Reranking

* BAAI/bge-reranker-v2-m3

### Vector Database

* Qdrant

### LLM

* OpenAI-compatible API

### Runtime

* Python

### Interface

* CLI

---

## Success Criteria

The project is considered successful if it can:

1. Index a document corpus.
2. Retrieve relevant information.
3. Generate grounded answers.
4. Display answer sources.
5. Support MCP-based knowledge access.
6. Demonstrate hybrid retrieval.
7. Demonstrate reranking.
8. Support conversational interaction through a LangGraph agent.

---

## Guiding Principle

The project is intended to demonstrate that modern enterprise RAG systems are not simply:

```text
Embedding → Vector Search → LLM
```

Instead, they are built as retrieval systems combining:

```text
Agent
  ↓
MCP
  ↓
Hybrid Retrieval
  ↓
Reranking
  ↓
Grounded Answer
```

Explainability and source attribution are first-class requirements.
