# Orchestration Service Documentation

Welcome to the comprehensive documentation for the industry-grade orchestration service. This documentation covers the new topology-based workflow system with parallel execution, advanced caching, and production-ready features.

## 📚 Documentation Overview

### Core Guides (Start Here)

These guides cover the essential concepts and configurations:

1. **[Topology Configuration](TOPOLOGY_CONFIGURATION.md)** ⭐
   - Learn about sequential, tree, graph, and hybrid topologies
   - Configure nodes, edges, and context passing
   - Choose the right topology for your use case
   - **Start here** if you're building new workflows

2. **[Execution Strategies](EXECUTION_STRATEGIES.md)** ⚡
   - Understand sequential, parallel, and hybrid execution
   - Optimize for latency, throughput, or balance
   - Configure resource limits and timeouts
   - **Read this** to improve performance

3. **[Cache Configuration](CACHE_CONFIGURATION.md)** 💰
   - Configure multi-layer caching (LLM, embedding, session, agent)
   - Reduce costs by 50%+ with proper caching
   - Optimize TTL, eviction policies, and cache size
   - **Essential** for cost optimization

4. **[Agent Behavior](AGENT_BEHAVIOR.md)** ✅
   - Configure output formats (JSON, code, text)
   - Set constraints and validation rules
   - Ensure reliable, consistent agent behavior
   - **Important** for production reliability

5. **[Migration Guide](MIGRATION_GUIDE.md)** 🔄
   - Migrate from old pattern-based workflows
   - Pattern-by-pattern conversion examples
   - Backward compatibility information
   - **Required** if upgrading from v1.0

6. **[Troubleshooting](TROUBLESHOOTING.md)** 🔧
   - Diagnose and fix common issues
   - Quick diagnostic commands
   - Solutions for topology, execution, cache, and config issues
   - **Reference** when things go wrong

### Additional Resources

- **[Model Configuration](MODEL_CONFIGURATION.md)** - Configure LLM models and providers
- **[RAG Setup](RAG_SETUP.md)** - Set up vector databases and RAG workflows
- **[Deployment Guide](../DEPLOYMENT.md)** - Production deployment quick reference
- **[Documentation Index](INDEX.md)** - Complete documentation index with learning paths

## 🚀 Quick Start Paths

### Path 1: New User (Building First Workflow)

```
1. Read main README.md
2. Follow Quick Start
3. Read Topology Configuration (focus on Sequential)
4. Create simple sequential workflow
5. Test and iterate
6. Explore Execution Strategies for optimization
```

**Estimated time:** 1-2 hours

### Path 2: Existing User (Migrating from v1.0)

```
1. Read Migration Guide overview
2. Understand new topology format
3. Convert one simple workflow
4. Test and compare results
5. Migrate remaining workflows
6. Optimize with Execution Strategies and Cache Configuration
```

**Estimated time:** 2-4 hours

### Path 3: Advanced User (Complex Workflows)

```
1. Read all Core Guides
2. Study graph topology examples
3. Configure hybrid execution strategy
4. Optimize cache configuration
5. Set up agent behavior validation
6. Build and test complex workflow
```

**Estimated time:** 4-8 hours

## 📖 Documentation by Use Case

### Use Case: Simple Chatbot

**Relevant Docs:**
- [Topology Configuration - Sequential](TOPOLOGY_CONFIGURATION.md#1-sequential-topology)
- [Execution Strategies - Sequential](EXECUTION_STRATEGIES.md#1-sequential-strategy)
- [Cache Configuration - Development](CACHE_CONFIGURATION.md#pattern-1-development-environment)

**Example:** `configs/templates/topologies/sequential_workflow.json`

### Use Case: Parallel Research

**Relevant Docs:**
- [Topology Configuration - Tree](TOPOLOGY_CONFIGURATION.md#2-tree-topology)
- [Execution Strategies - Parallel](EXECUTION_STRATEGIES.md#2-parallel-strategy)
- [Cache Configuration - Cost-Optimized](CACHE_CONFIGURATION.md#pattern-3-cost-optimized)

**Example:** `configs/templates/complete_examples/research_workflow.json`

### Use Case: Complex Decision Workflow

**Relevant Docs:**
- [Topology Configuration - Graph](TOPOLOGY_CONFIGURATION.md#3-graph-topology)
- [Execution Strategies - Hybrid](EXECUTION_STRATEGIES.md#3-hybrid-strategy)
- [Agent Behavior - Validation](AGENT_BEHAVIOR.md#validation-configuration)

**Example:** `configs/templates/topologies/graph_topology.json`

### Use Case: Production API

**Relevant Docs:**
- [Execution Strategies - Performance Tuning](EXECUTION_STRATEGIES.md#performance-tuning)
- [Cache Configuration - Production](CACHE_CONFIGURATION.md#pattern-2-production-environment)
- [Troubleshooting - High Load](TROUBLESHOOTING.md#issue-high-resource-usage)

**Example:** `configs/templates/complete_examples/customer_support_workflow.json`

## 🎯 Common Tasks

### Create a Sequential Workflow

1. Read: [Topology Configuration - Sequential](TOPOLOGY_CONFIGURATION.md#1-sequential-topology)
2. Copy: `configs/templates/topologies/sequential_workflow.json`
3. Modify: Update agent IDs and configuration
4. Deploy: `POST /api/v1/workflows`

### Enable Parallel Execution

1. Read: [Execution Strategies - Parallel](EXECUTION_STRATEGIES.md#2-parallel-strategy)
2. Update workflow:
   ```json
   {
     "execution_strategy": "parallel",
     "strategy_config": {
       "max_concurrent": 5
     }
   }
   ```
3. Test and measure performance improvement

### Configure Caching

1. Read: [Cache Configuration - Global](CACHE_CONFIGURATION.md#global-configuration)
2. Edit: `configs/cache.json`
3. Set TTL and eviction policy
4. Monitor: Check cache hit rate metrics

### Validate Agent Output

1. Read: [Agent Behavior - Output Format](AGENT_BEHAVIOR.md#output-format-configuration)
2. Add JSON schema to agent config
3. Enable validation
4. Test with sample inputs

### Migrate Old Workflow

1. Read: [Migration Guide - Pattern by Pattern](MIGRATION_GUIDE.md#pattern-by-pattern-migration)
2. Identify your pattern (two_agent, sequential, group_chat, nested)
3. Follow conversion guide for your pattern
4. Test migrated workflow
5. Compare results with old format

### Fix Topology Errors

1. Read: [Troubleshooting - Topology Issues](TROUBLESHOOTING.md#topology-configuration-issues)
2. Run validation: `POST /api/v1/workflows/validate`
3. Fix identified issues
4. Re-validate

## 📊 Configuration Examples

### Complete Workflow Examples

Located in `configs/templates/complete_examples/`:

- **[research_workflow.json](../configs/templates/complete_examples/research_workflow.json)** - Tree topology with parallel research
- **[code_review_workflow.json](../configs/templates/complete_examples/code_review_workflow.json)** - Graph topology with quality control
- **[customer_support_workflow.json](../configs/templates/complete_examples/customer_support_workflow.json)** - Hybrid topology for support

### Topology Templates

Located in `configs/templates/topologies/`:

- **[sequential_workflow.json](../configs/templates/topologies/sequential_workflow.json)** - Simple sequential chain
- **[tree_topology.json](../configs/templates/topologies/tree_topology.json)** - Parallel branches
- **[graph_topology.json](../configs/templates/topologies/graph_topology.json)** - Complex routing with cycles
- **[hybrid_topology.json](../configs/templates/topologies/hybrid_topology.json)** - Mixed execution

### Configuration Templates

Located in `configs/templates/`:

- **Execution strategies**: `execution/`
- **Cache configurations**: `cache/`
- **Agent behaviors**: `agents/`

## 🔍 Finding Information

### By Topic

- **Topologies**: [Topology Configuration](TOPOLOGY_CONFIGURATION.md)
- **Performance**: [Execution Strategies](EXECUTION_STRATEGIES.md)
- **Cost Optimization**: [Cache Configuration](CACHE_CONFIGURATION.md)
- **Reliability**: [Agent Behavior](AGENT_BEHAVIOR.md)
- **Upgrading**: [Migration Guide](MIGRATION_GUIDE.md)
- **Problems**: [Troubleshooting](TROUBLESHOOTING.md)

### By Question

- "How do I make my workflow faster?" → [Execution Strategies](EXECUTION_STRATEGIES.md)
- "How do I reduce costs?" → [Cache Configuration](CACHE_CONFIGURATION.md)
- "How do I ensure consistent output?" → [Agent Behavior](AGENT_BEHAVIOR.md)
- "How do I upgrade from v1.0?" → [Migration Guide](MIGRATION_GUIDE.md)
- "Why isn't my workflow working?" → [Troubleshooting](TROUBLESHOOTING.md)
- "What topology should I use?" → [Topology Configuration - Choosing](TOPOLOGY_CONFIGURATION.md#choosing-the-right-topology)

### By Error Message

- "Unreachable nodes detected" → [Troubleshooting - Topology](TROUBLESHOOTING.md#issue-unreachable-nodes-detected)
- "Cycle detected without termination" → [Troubleshooting - Topology](TROUBLESHOOTING.md#issue-cycle-detected-without-termination-condition)
- "Invalid agent reference" → [Troubleshooting - Topology](TROUBLESHOOTING.md#issue-invalid-agent-reference)
- "Workflow timeout" → [Troubleshooting - Execution](TROUBLESHOOTING.md#issue-workflow-timeout)
- "Low cache hit rate" → [Troubleshooting - Cache](TROUBLESHOOTING.md#issue-low-cache-hit-rate)

## 🛠️ Tools and Utilities

### Validation Tools

```bash
# Validate topology
curl -X POST http://localhost:8000/api/v1/workflows/validate \
  -d @my_workflow.json

# Validate configuration
curl -X POST http://localhost:8000/api/v1/configs/validate \
  -d @my_config.json
```

### Monitoring Tools

```bash
# Check metrics
curl http://localhost:8000/api/v1/metrics

# Check health
curl http://localhost:8000/health

# Check logs
curl http://localhost:8000/api/v1/logs?level=ERROR
```

### Migration Tools

```bash
# Automated migration script
python scripts/migrate_workflow.py old_workflow.json > new_workflow.json

# Validation after migration
python scripts/validate_topology.py new_workflow.json
```

## 📝 Documentation Standards

All documentation follows these standards:

- **Clear Examples**: Every concept includes working examples
- **Complete Configurations**: All JSON examples are complete and valid
- **Troubleshooting**: Common issues and solutions included
- **Cross-References**: Links to related documentation
- **Use Cases**: Real-world scenarios and patterns
- **Best Practices**: Recommended approaches highlighted

## 🤝 Contributing

Found an issue or want to improve the docs?

1. Check [Documentation Index](INDEX.md) for existing content
2. Review [Contributing Guidelines](../CONTRIBUTING.md)
3. Submit issue or pull request
4. Follow documentation style guide

## 📞 Support

- **Documentation Issues**: GitHub Issues
- **Questions**: Community discussions
- **Examples**: Check `configs/templates/complete_examples/`
- **API Reference**: http://localhost:8000/docs

## 🗺️ Documentation Map

```
docs/
├── README.md (this file)           # Documentation overview
├── INDEX.md                        # Complete index with learning paths
├── TOPOLOGY_CONFIGURATION.md       # Workflow topology guide
├── MIGRATION_GUIDE.md              # Migration from v1.0
├── EXECUTION_STRATEGIES.md         # Execution optimization
├── CACHE_CONFIGURATION.md          # Caching guide
├── AGENT_BEHAVIOR.md               # Agent configuration
├── TROUBLESHOOTING.md              # Problem solving
├── MODEL_CONFIGURATION.md          # LLM model setup
└── RAG_SETUP.md                    # Vector database setup
```

## 🎓 Learning Resources

### Video Tutorials (Coming Soon)

- Getting Started with Topologies
- Building Your First Parallel Workflow
- Optimizing Cache Configuration
- Advanced Graph Topologies

### Blog Posts (Coming Soon)

- "5 Ways to Reduce LLM Costs with Caching"
- "When to Use Each Topology Type"
- "Migrating from v1.0: A Complete Guide"
- "Building Production-Ready Workflows"

## 📅 Version History

### Version 2.0 (Current)

- ✅ New topology-based workflow system
- ✅ Parallel and hybrid execution strategies
- ✅ Multi-layer cache configuration
- ✅ Agent behavior validation
- ✅ Complete migration guide
- ✅ Comprehensive documentation

### Version 1.0 (Legacy)

- Pattern-based workflows
- Sequential execution only
- Basic caching
- See [Migration Guide](MIGRATION_GUIDE.md)

## 🚀 Next Steps

1. **New Users**: Start with [Topology Configuration](TOPOLOGY_CONFIGURATION.md)
2. **Existing Users**: Read [Migration Guide](MIGRATION_GUIDE.md)
3. **Advanced Users**: Explore all Core Guides
4. **Having Issues**: Check [Troubleshooting](TROUBLESHOOTING.md)

---

**Need help?** Check the [Documentation Index](INDEX.md) or [Troubleshooting Guide](TROUBLESHOOTING.md).

