import { Component, inject, OnInit, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { WorkflowConfig, ConversationPattern } from '../../models/workflow.model';

interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  type: 'entry' | 'recipient' | 'agent' | 'manager';
  color: string;
}

interface GraphEdge {
  from: string;
  to: string;
  label?: string;
  bidirectional?: boolean;
}

@Component({
  selector: 'app-workflow-visualizer-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatCardModule, MatIconModule, MatTooltipModule],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>account_tree</mat-icon>
      Workflow: {{ data.workflow.name }}
    </h2>
    <mat-dialog-content>
      <!-- Workflow Info Header -->
      <div class="workflow-header">
        <div class="info-chip pattern">
          <mat-icon>{{ getPatternIcon() }}</mat-icon>
          <span>{{ data.workflow.pattern | uppercase }}</span>
        </div>
        <div class="info-chip" *ngIf="data.workflow.enabled !== false">
          <mat-icon>check_circle</mat-icon>
          <span>Enabled</span>
        </div>
        <div class="info-chip disabled" *ngIf="data.workflow.enabled === false">
          <mat-icon>cancel</mat-icon>
          <span>Disabled</span>
        </div>
        <div class="info-chip">
          <mat-icon>repeat</mat-icon>
          <span>Max Turns: {{ data.workflow.max_turns || 10 }}</span>
        </div>
      </div>

      <!-- Graph Visualization -->
      <div class="graph-container">
        <div class="graph-title">
          <mat-icon>hub</mat-icon>
          <span>Agent Flow Diagram</span>
        </div>
        <svg #graphSvg class="workflow-graph" [attr.viewBox]="viewBox">
          <!-- Definitions for markers (arrows) -->
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#1976d2" />
            </marker>
            <marker id="arrowhead-gray" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
            </marker>
            <marker id="arrowhead-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#4caf50" />
            </marker>
            <!-- Gradient for nodes -->
            <linearGradient id="entryGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color:#4caf50;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#388e3c;stop-opacity:1" />
            </linearGradient>
            <linearGradient id="recipientGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color:#2196f3;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#1565c0;stop-opacity:1" />
            </linearGradient>
            <linearGradient id="agentGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color:#ff9800;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#ef6c00;stop-opacity:1" />
            </linearGradient>
            <linearGradient id="managerGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color:#9c27b0;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#6a1b9a;stop-opacity:1" />
            </linearGradient>
            <!-- Shadow filter -->
            <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.3"/>
            </filter>
          </defs>

          <!-- Draw edges -->
          <g class="edges">
            <g *ngFor="let edge of edges">
              <line
                [attr.x1]="getNodeById(edge.from)?.x"
                [attr.y1]="getNodeById(edge.from)?.y"
                [attr.x2]="getEdgeEndX(edge)"
                [attr.y2]="getEdgeEndY(edge)"
                stroke="#1976d2"
                stroke-width="2"
                marker-end="url(#arrowhead)"
                class="edge-line"
              />
              <!-- Edge label -->
              <text
                *ngIf="edge.label"
                [attr.x]="(getNodeById(edge.from)!.x + getNodeById(edge.to)!.x) / 2"
                [attr.y]="(getNodeById(edge.from)!.y + getNodeById(edge.to)!.y) / 2 - 10"
                text-anchor="middle"
                class="edge-label"
              >
                {{ edge.label }}
              </text>
              <!-- Bidirectional arrow -->
              <line
                *ngIf="edge.bidirectional"
                [attr.x1]="getNodeById(edge.to)?.x"
                [attr.y1]="(getNodeById(edge.to)?.y || 0) + 5"
                [attr.x2]="(getNodeById(edge.from)?.x || 0) + 50"
                [attr.y2]="(getNodeById(edge.from)?.y || 0) + 5"
                stroke="#4caf50"
                stroke-width="2"
                stroke-dasharray="5,3"
                marker-end="url(#arrowhead-green)"
                class="edge-line return"
              />
            </g>
          </g>

          <!-- Draw nodes -->
          <g class="nodes">
            <g *ngFor="let node of nodes" class="node-group" [attr.transform]="'translate(' + node.x + ',' + node.y + ')'">
              <!-- Node circle -->
              <circle
                r="40"
                [attr.fill]="'url(#' + node.type + 'Gradient)'"
                filter="url(#shadow)"
                class="node-circle"
              />
              <!-- Node icon -->
              <text
                y="-5"
                text-anchor="middle"
                class="node-icon"
                fill="white"
              >
                {{ getNodeIcon(node.type) }}
              </text>
              <!-- Node label -->
              <text
                y="12"
                text-anchor="middle"
                class="node-label"
                fill="white"
              >
                {{ truncateLabel(node.label) }}
              </text>
              <!-- Node type badge -->
              <g [attr.transform]="'translate(25, -30)'">
                <rect x="0" y="0" width="40" height="18" rx="9" [attr.fill]="getTypeBadgeColor(node.type)" />
                <text x="20" y="13" text-anchor="middle" class="type-badge">{{ getTypeBadgeText(node.type) }}</text>
              </g>
            </g>
          </g>

          <!-- Legend -->
          <g class="legend" transform="translate(20, 20)">
            <rect x="0" y="0" width="120" height="100" fill="white" stroke="#e0e0e0" rx="5" opacity="0.9"/>
            <text x="10" y="20" class="legend-title">Legend</text>
            <circle cx="20" cy="40" r="8" fill="url(#entryGradient)" />
            <text x="35" y="44" class="legend-text">Entry Agent</text>
            <circle cx="20" cy="60" r="8" fill="url(#recipientGradient)" />
            <text x="35" y="64" class="legend-text">Recipient</text>
            <circle cx="20" cy="80" r="8" fill="url(#agentGradient)" />
            <text x="35" y="84" class="legend-text">Agent</text>
          </g>
        </svg>
      </div>

      <!-- Workflow Details -->
      <div class="workflow-details">
        <div class="detail-section" *ngIf="data.workflow.pattern === 'two_agent'">
          <h4><mat-icon>people</mat-icon> Two-Agent Configuration</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Entry Agent (Sender):</span>
              <span class="value">{{ data.workflow.entry_agent_id }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Recipient Agent:</span>
              <span class="value">{{ data.workflow.recipient_agent_id || 'Not set' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Summary Method:</span>
              <span class="value">{{ data.workflow.summary_method || 'last_msg' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" *ngIf="data.workflow.steps && data.workflow.steps.length > 0">
          <h4><mat-icon>format_list_numbered</mat-icon> Sequential Steps</h4>
          <div class="steps-timeline">
            <div class="step-item" *ngFor="let step of data.workflow.steps; let i = index">
              <div class="step-number">{{ i + 1 }}</div>
              <div class="step-info">
                <div class="step-agents">
                  <span class="agent sender">{{ step.sender_id }}</span>
                  <mat-icon>arrow_forward</mat-icon>
                  <span class="agent recipient">{{ step.recipient_id }}</span>
                </div>
                <div class="step-meta">
                  Max turns: {{ step.max_turns }} | Summary: {{ step.summary_method }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="detail-section" *ngIf="data.workflow.group_chat">
          <h4><mat-icon>groups</mat-icon> Group Chat Configuration</h4>
          <div class="detail-grid">
            <div class="detail-item full-width">
              <span class="label">Participants:</span>
              <div class="agent-chips">
                <span class="agent-chip" *ngFor="let agent of data.workflow.group_chat.agents">
                  {{ agent }}
                </span>
              </div>
            </div>
            <div class="detail-item">
              <span class="label">Max Rounds:</span>
              <span class="value">{{ data.workflow.group_chat.max_round }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Speaker Selection:</span>
              <span class="value">{{ data.workflow.group_chat.speaker_selection_method }}</span>
            </div>
          </div>
        </div>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Close</button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
      display: block;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 12px;
      color: #1976d2;
      
      mat-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
      }
    }

    mat-dialog-content {
      width: 100%;
      padding: 20px 24px;
      box-sizing: border-box;
      overflow: auto;
      flex: 1;
      
      &::-webkit-scrollbar {
        width: 12px;
        height: 12px;
      }
      
      &::-webkit-scrollbar-track {
        background: #e2e8f0;
        border-radius: 6px;
      }
      
      &::-webkit-scrollbar-thumb {
        background: #94a3b8;
        border-radius: 6px;
        border: 3px solid #e2e8f0;
        
        &:hover {
          background: #64748b;
        }
      }
    }

    .workflow-header {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .info-chip {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: #e3f2fd;
      border-radius: 16px;
      font-size: 13px;
      color: #1565c0;

      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }

      &.pattern {
        background: #1976d2;
        color: white;
      }

      &.disabled {
        background: #ffebee;
        color: #c62828;
      }
    }

    .graph-container {
      background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
      border: 1px solid #e0e0e0;
    }

    .graph-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
      font-weight: 500;
      color: #424242;

      mat-icon {
        color: #1976d2;
      }
    }

    .workflow-graph {
      width: 100%;
      height: 350px;
      background: white;
      border-radius: 8px;
      border: 1px solid #e0e0e0;
    }

    .edge-line {
      transition: stroke-width 0.2s;
      
      &:hover {
        stroke-width: 3;
      }
    }

    .edge-label {
      font-size: 11px;
      fill: #666;
      font-weight: 500;
    }

    .node-circle {
      cursor: pointer;
      transition: transform 0.2s;
    }

    .node-group:hover .node-circle {
      transform: scale(1.1);
    }

    .node-icon {
      font-size: 20px;
      font-family: 'Material Icons';
    }

    .node-label {
      font-size: 11px;
      font-weight: 600;
    }

    .type-badge {
      font-size: 9px;
      fill: white;
      font-weight: 600;
    }

    .legend-title {
      font-size: 12px;
      font-weight: 600;
      fill: #424242;
    }

    .legend-text {
      font-size: 10px;
      fill: #666;
    }

    .workflow-details {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .detail-section {
      background: #fafafa;
      border-radius: 8px;
      padding: 16px;
      border: 1px solid #e0e0e0;

      h4 {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 0 0 16px 0;
        color: #1976d2;
        font-size: 15px;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
        }
      }
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }

    .detail-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      &.full-width {
        grid-column: span 2;
      }

      .label {
        font-size: 12px;
        color: #666;
        font-weight: 500;
      }

      .value {
        font-size: 14px;
        color: #333;
      }
    }

    .agent-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 4px;
    }

    .agent-chip {
      padding: 4px 12px;
      background: #e3f2fd;
      border-radius: 12px;
      font-size: 12px;
      color: #1565c0;
    }

    .steps-timeline {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .step-item {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }

    .step-number {
      width: 28px;
      height: 28px;
      background: #1976d2;
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 13px;
      flex-shrink: 0;
    }

    .step-info {
      flex: 1;
    }

    .step-agents {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .agent {
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 13px;
        font-weight: 500;

        &.sender {
          background: #e8f5e9;
          color: #2e7d32;
        }

        &.recipient {
          background: #e3f2fd;
          color: #1565c0;
        }
      }

      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: #666;
      }
    }

    .step-meta {
      font-size: 12px;
      color: #666;
    }
  `]
})
export class WorkflowVisualizerDialogComponent implements OnInit {
  data = inject<{ workflow: WorkflowConfig }>(MAT_DIALOG_DATA);
  
  nodes: GraphNode[] = [];
  edges: GraphEdge[] = [];
  viewBox = '0 0 800 350';

  ngOnInit(): void {
    this.buildGraph();
  }

  buildGraph(): void {
    const workflow = this.data.workflow;
    this.nodes = [];
    this.edges = [];

    if (workflow.nodes && workflow.nodes.length > 0) {
      this.buildCustomGraph();
    } else {
      switch (workflow.pattern) {
        case ConversationPattern.TWO_AGENT:
          this.buildTwoAgentGraph();
          break;
        case ConversationPattern.SEQUENTIAL:
          this.buildSequentialGraph();
          break;
        case ConversationPattern.GROUP_CHAT:
          this.buildGroupChatGraph();
          break;
        case ConversationPattern.NESTED:
          this.buildNestedGraph();
          break;
        default:
          this.buildTwoAgentGraph();
      }
    }
  }

  buildCustomGraph(): void {
    const workflow = this.data.workflow;
    if (!workflow.nodes) return;

    // Map nodes
    this.nodes = workflow.nodes.map(node => ({
      id: node.id,
      label: node.agent_id,
      x: node.position.x,
      y: node.position.y,
      type: node.id === workflow.entry_agent_id ? 'entry' : 'agent',
      color: node.id === workflow.entry_agent_id ? '#4caf50' : '#ff9800'
    }));

    // Map connections
    if (workflow.connections) {
      this.edges = workflow.connections.map(conn => ({
        from: conn.from_node,
        to: conn.to_node,
        label: conn.type
      }));
    }
  }

  buildTwoAgentGraph(): void {
    const workflow = this.data.workflow;
    
    // Entry agent (left)
    this.nodes.push({
      id: workflow.entry_agent_id,
      label: workflow.entry_agent_id,
      x: 250,
      y: 175,
      type: 'entry',
      color: '#4caf50'
    });

    // Recipient agent (right)
    if (workflow.recipient_agent_id) {
      this.nodes.push({
        id: workflow.recipient_agent_id,
        label: workflow.recipient_agent_id,
        x: 550,
        y: 175,
        type: 'recipient',
        color: '#2196f3'
      });

      // Edge from entry to recipient
      this.edges.push({
        from: workflow.entry_agent_id,
        to: workflow.recipient_agent_id,
        label: 'message',
        bidirectional: true
      });
    }
  }

  buildSequentialGraph(): void {
    const workflow = this.data.workflow;
    const steps = workflow.steps || [];
    
    // Collect unique agents
    const agentIds = new Set<string>();
    agentIds.add(workflow.entry_agent_id);
    steps.forEach(step => {
      agentIds.add(step.sender_id);
      agentIds.add(step.recipient_id);
    });

    const agents = Array.from(agentIds);
    const spacing = 700 / (agents.length + 1);

    // Create nodes
    agents.forEach((agentId, index) => {
      this.nodes.push({
        id: agentId,
        label: agentId,
        x: spacing * (index + 1),
        y: 175,
        type: agentId === workflow.entry_agent_id ? 'entry' : 'agent',
        color: agentId === workflow.entry_agent_id ? '#4caf50' : '#ff9800'
      });
    });

    // Create edges from steps
    steps.forEach((step, index) => {
      this.edges.push({
        from: step.sender_id,
        to: step.recipient_id,
        label: `Step ${index + 1}`
      });
    });
  }

  buildGroupChatGraph(): void {
    const workflow = this.data.workflow;
    const groupChat = workflow.group_chat;
    
    if (!groupChat) return;

    const agents = groupChat.agents;
    const centerX = 400;
    const centerY = 175;
    const radius = 120;

    // Create nodes in a circle
    agents.forEach((agentId, index) => {
      const angle = (2 * Math.PI * index) / agents.length - Math.PI / 2;
      this.nodes.push({
        id: agentId,
        label: agentId,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        type: agentId === workflow.entry_agent_id ? 'entry' : 'agent',
        color: agentId === workflow.entry_agent_id ? '#4caf50' : '#ff9800'
      });
    });

    // Add manager in center
    this.nodes.push({
      id: 'manager',
      label: 'GroupChatManager',
      x: centerX,
      y: centerY,
      type: 'manager',
      color: '#9c27b0'
    });

    // Connect all agents to manager
    agents.forEach(agentId => {
      this.edges.push({
        from: agentId,
        to: 'manager',
        bidirectional: true
      });
    });
  }

  buildNestedGraph(): void {
    // Simplified nested graph - similar to two-agent with nested indicator
    this.buildTwoAgentGraph();
  }

  getNodeById(id: string): GraphNode | undefined {
    return this.nodes.find(n => n.id === id);
  }

  getEdgeEndX(edge: GraphEdge): number {
    const toNode = this.getNodeById(edge.to);
    const fromNode = this.getNodeById(edge.from);
    if (!toNode || !fromNode) return 0;
    
    // Calculate point on circle edge
    const dx = toNode.x - fromNode.x;
    const dy = toNode.y - fromNode.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    return toNode.x - (dx / dist) * 45;
  }

  getEdgeEndY(edge: GraphEdge): number {
    const toNode = this.getNodeById(edge.to);
    const fromNode = this.getNodeById(edge.from);
    if (!toNode || !fromNode) return 0;
    
    const dx = toNode.x - fromNode.x;
    const dy = toNode.y - fromNode.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    return toNode.y - (dy / dist) * 45;
  }

  truncateLabel(label: string): string {
    return label.length > 12 ? label.substring(0, 10) + '..' : label;
  }

  getPatternIcon(): string {
    switch (this.data.workflow.pattern) {
      case ConversationPattern.TWO_AGENT: return 'people';
      case ConversationPattern.SEQUENTIAL: return 'format_list_numbered';
      case ConversationPattern.GROUP_CHAT: return 'groups';
      case ConversationPattern.NESTED: return 'account_tree';
      default: return 'hub';
    }
  }

  getNodeIcon(type: string): string {
    switch (type) {
      case 'entry': return '▶';
      case 'recipient': return '◉';
      case 'manager': return '★';
      default: return '●';
    }
  }

  getTypeBadgeColor(type: string): string {
    switch (type) {
      case 'entry': return '#2e7d32';
      case 'recipient': return '#1565c0';
      case 'manager': return '#6a1b9a';
      default: return '#ef6c00';
    }
  }

  getTypeBadgeText(type: string): string {
    switch (type) {
      case 'entry': return 'ENTRY';
      case 'recipient': return 'RECV';
      case 'manager': return 'MGR';
      default: return 'AGENT';
    }
  }
}
