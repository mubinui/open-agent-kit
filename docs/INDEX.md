# Documentation Index

## Getting Started

Start here if you're new to the orchestration service:

1. **[README](../README.md)** - Project overview and quick start
2. **[Deployment Guide](../DEPLOYMENT.md)** - Quick deployment reference
3. **[Model Configuration](MODEL_CONFIGURATION.md)** - Configure LLM models

## Core Concepts

Understand the new topology-based system:

1. **[Topology Configuration](TOPOLOGY_CONFIGURATION.md)** - Learn about workflow topologies
   - Sequential, tree, graph, and hybrid topologies
   - Node and edge configuration
   - Context passing strategies
   - Choosing the right topology

2. **[Execution Strategies](EXECUTION_STRATEGIES.md)** - Optimize workflow execution
   - Sequential, parallel, and hybrid strategies
   - Performance comparison
   - Configuration options
   - Best practices

3. **[Cache Configuration](CACHE_CONFIGURATION.md)** - Reduce costs and improve performance
   - Multi-layer caching system
   - Configuration hierarchy
   - Eviction policies
   - Optimization strategies

4. **[Agent Behavior](AGENT_BEHAVIOR.md)** - Configure reliable agent behavior
   - Output format validation
   - Constraints and security
   - Custom validation
   - Complete examples

## Migration

Upgrade from the old system:

1. **[Migration Guide](MIGRATION_GUIDE.md)** - Step-by-step migration
   - Pattern-by-pattern conversion
   - Backward compatibility
   - Migration tools
   - Testing strategies

## Operations

Run and maintain the service:

1. **[Troubleshooting](TROUBLESHOOTING.md)** - Diagnose and fix issues
   - Topology issues
   - Execution issues
   - Cache issues
   - Configuration issues
   - Infrastructure issues

2. **[RAG Setup](RAG_SETUP.md)** - Configure vector databases
   - Qdrant setup
   - Document ingestion
   - RAG workflows

## Configuration Reference

Detailed configuration examples:

1. **[Configuration Templates](../configs/templates/README.md)** - Complete template guide
   - Topology templates
   - Execution strategy templates
   - Cache configuration templates
   - Agent behavior templates
   - Complete workflow examples

2. **[Configuration Hierarchy](../configs/templates/CONFIGURATION_HIERARCHY.md)** - Understanding overrides
3. **[Quick Reference](../configs/templates/QUICK_REFERENCE.md)** - Quick configuration lookup

## Learning Path

### For New Users

```
1. Read README
2. Follow Quick Start
3. Read Topology Configuration
4. Try simple sequential workflow
5. Explore complete examples
```

### For Existing Users (Migration)

```
1. Read Migration Guide
2. Understand new topology format
3. Convert one workflow
4. Test and compare
5. Migrate remaining workflows
```

### For Advanced Users

```
1. Read all core concept docs
2. Study execution strategies
3. Optimize cache configuration
4. Configure agent behaviors
5. Build complex graph topologies
```

## Quick Links

### Common Tasks

- **Create a sequential workflow**: [Topology Configuration - Sequential](TOPOLOGY_CONFIGURATION.md#1-sequential-topology)
- **Enable parallel execution**: [Execution Strategies - Parallel](EXECUTION_STRATEGIES.md#2-parallel-strategy)
- **Configure caching**: [Cache Configuration - Global](CACHE_CONFIGURATION.md#global-configuration)
- **Validate agent output**: [Agent Behavior - Validation](AGENT_BEHAVIOR.md#validation-configuration)
- **Migrate old workflow**: [Migration Guide - Pattern by Pattern](MIGRATION_GUIDE.md#pattern-by-pattern-migration)
- **Fix topology errors**: [Troubleshooting - Topology](TROUBLESHOOTING.md#topology-configuration-issues)
- **Use default workflow**: [README - Default Workflow](../README.md#default-workflow)
- **Configure context management**: [README - Context Management](../README.md#context-management)

### Configuration Examples

- **Tree topology**: [configs/templates/topologies/tree_topology.json](../configs/templates/topologies/tree_topology.json)
- **Graph topology**: [configs/templates/topologies/graph_topology.json](../configs/templates/topologies/graph_topology.json)
- **Research workflow**: [configs/templates/complete_examples/research_workflow.json](../configs/templates/complete_examples/research_workflow.json)
- **Code review workflow**: [configs/templates/complete_examples/code_review_workflow.json](../configs/templates/complete_examples/code_review_workflow.json)

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/api/v1/metrics

## Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| Topology Configuration | ✅ Complete | 2024-12-10 |
| Migration Guide | ✅ Complete | 2024-12-10 |
| Execution Strategies | ✅ Complete | 2024-12-10 |
| Cache Configuration | ✅ Complete | 2024-12-10 |
| Agent Behavior | ✅ Complete | 2024-12-10 |
| Troubleshooting | ✅ Complete | 2024-12-10 |
| Model Configuration | ✅ Complete | 2024-11-26 |
| RAG Setup | ✅ Complete | 2024-12-03 |
| Default Workflow & Context | ✅ Complete | 2024-12-11 |

## Contributing to Documentation

Found an issue or want to improve the docs?

1. Check existing documentation
2. Identify gaps or errors
3. Submit issue or pull request
4. Follow documentation style guide

### Documentation Style Guide

- Use clear, concise language
- Include code examples
- Provide complete configurations
- Add troubleshooting sections
- Link to related documents
- Keep examples up to date

## Support

- **GitHub Issues**: Report documentation issues
- **Community**: Ask questions and share knowledge
- **Examples**: Check `configs/templates/complete_examples/`

## Version History

### Version 2.0 (Current)

- New topology-based workflow system
- Parallel and hybrid execution strategies
- Multi-layer cache configuration
- Agent behavior validation
- Complete migration guide

### Version 1.0 (Legacy)

- Pattern-based workflows
- Sequential execution only
- Basic caching
- See [Migration Guide](MIGRATION_GUIDE.md) for upgrade path

