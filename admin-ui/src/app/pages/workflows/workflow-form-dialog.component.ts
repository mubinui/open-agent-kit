import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { WorkflowConfig, ConversationPattern } from '../../models/workflow.model';
import { ApiService } from '../../services/api.service';
import { AgentConfig } from '../../models/agent.model';

@Component({
  selector: 'app-workflow-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCheckboxModule,
    MatIconModule,
    MatTooltipModule
  ],
  template: `
    <h2 mat-dialog-title>{{ isEdit() ? 'Edit Workflow' : 'Create Workflow' }}</h2>
    <mat-dialog-content>
      <form>
        <!-- Basic Info Section -->
        <div class="section-header">
          <mat-icon>info</mat-icon>
          <span>Basic Information</span>
        </div>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>ID</mat-label>
          <input matInput [(ngModel)]="workflow.id" name="id" required [disabled]="isEdit()"
                 pattern="^[a-z0-9_-]+$">
          <mat-hint>Lowercase letters, numbers, underscores, and hyphens only</mat-hint>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Name</mat-label>
          <input matInput [(ngModel)]="workflow.name" name="name" required>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Description</mat-label>
          <textarea matInput [(ngModel)]="workflow.description" name="description" rows="2"></textarea>
        </mat-form-field>

        <mat-checkbox [(ngModel)]="workflow.enabled" name="enabled" class="checkbox-field">
          Enabled
        </mat-checkbox>

        <!-- Pattern Configuration Section -->
        <div class="section-header">
          <mat-icon>account_tree</mat-icon>
          <span>Pattern Configuration</span>
        </div>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Pattern</mat-label>
          <mat-select [(ngModel)]="workflow.pattern" name="pattern" required>
            <mat-option [value]="ConversationPattern.TWO_AGENT">Two Agent</mat-option>
            <mat-option [value]="ConversationPattern.SEQUENTIAL">Sequential</mat-option>
            <mat-option [value]="ConversationPattern.GROUP_CHAT">Group Chat</mat-option>
            <mat-option [value]="ConversationPattern.NESTED">Nested</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Entry Agent (Sender)</mat-label>
          <mat-select [(ngModel)]="workflow.entry_agent_id" name="entry_agent_id" required>
            <mat-option *ngFor="let agent of availableAgents()" [value]="agent.id">
              {{ agent.name }} ({{ agent.id }})
            </mat-option>
          </mat-select>
          <mat-hint>The agent that initiates the conversation</mat-hint>
        </mat-form-field>

        <!-- Two-Agent Pattern Fields -->
        <ng-container *ngIf="workflow.pattern === ConversationPattern.TWO_AGENT">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Recipient Agent</mat-label>
            <mat-select [(ngModel)]="workflow.recipient_agent_id" name="recipient_agent_id" required>
              <mat-option *ngFor="let agent of availableAgents()" [value]="agent.id">
                {{ agent.name }} ({{ agent.id }})
              </mat-option>
            </mat-select>
            <mat-hint>The agent that responds (should have LLM config)</mat-hint>
          </mat-form-field>

          <div class="row">
            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Max Turns</mat-label>
              <input matInput type="number" [(ngModel)]="workflow.max_turns" name="max_turns" 
                     min="1" max="100" required>
              <mat-hint>Maximum conversation turns</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Summary Method</mat-label>
              <mat-select [(ngModel)]="workflow.summary_method" name="summary_method">
                <mat-option value="last_msg">Last Message</mat-option>
                <mat-option value="reflection_with_llm">Reflection with LLM</mat-option>
              </mat-select>
            </mat-form-field>
          </div>
        </ng-container>

        <!-- Group Chat Pattern Fields -->
        <ng-container *ngIf="workflow.pattern === ConversationPattern.GROUP_CHAT">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Group Agents</mat-label>
            <mat-select [(ngModel)]="groupAgents" name="group_agents" multiple required>
              <mat-option *ngFor="let agent of availableAgents()" [value]="agent.id">
                {{ agent.name }} ({{ agent.id }})
              </mat-option>
            </mat-select>
            <mat-hint>Select multiple agents for the group chat</mat-hint>
          </mat-form-field>

          <div class="row">
            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Max Rounds</mat-label>
              <input matInput type="number" [(ngModel)]="groupMaxRound" name="group_max_round" 
                     min="1" max="100">
            </mat-form-field>

            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Speaker Selection</mat-label>
              <mat-select [(ngModel)]="groupSpeakerMethod" name="group_speaker_method">
                <mat-option value="auto">Auto (LLM)</mat-option>
                <mat-option value="round_robin">Round Robin</mat-option>
                <mat-option value="random">Random</mat-option>
              </mat-select>
            </mat-form-field>
          </div>
        </ng-container>

        <!-- Settings Section -->
        <div class="section-header">
          <mat-icon>settings</mat-icon>
          <span>Settings</span>
        </div>

        <div class="row">
          <mat-form-field appearance="outline" class="half-width">
            <mat-label>Workflow Type</mat-label>
            <mat-select [(ngModel)]="workflow.workflow_type" name="workflow_type">
              <mat-option value="sequential">Sequential</mat-option>
              <mat-option value="chatbot">Chatbot</mat-option>
              <mat-option value="tree">Tree</mat-option>
              <mat-option value="custom">Custom</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" class="half-width">
            <mat-label>Persistence</mat-label>
            <mat-select [(ngModel)]="workflow.persistence" name="persistence">
              <mat-option value="postgres">PostgreSQL</mat-option>
              <mat-option value="mongo_only">MongoDB Only</mat-option>
            </mat-select>
          </mat-form-field>
        </div>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" (click)="onSave()" [disabled]="!isValid()">Save</button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
      display: block;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 1.25rem;
      font-weight: 600;
      color: #1e293b;
    }

    mat-dialog-content {
      width: 100%;
      padding: 20px 24px;
      box-sizing: border-box;
      overflow-x: auto;
      overflow-y: auto;
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

    .full-width {
      width: 100%;
      margin-bottom: 12px;
      box-sizing: border-box;
    }
    .half-width {
      flex: 1;
      min-width: 0;
    }

    .row {
      display: flex;
      gap: 16px;
      margin-bottom: 12px;
      width: 100%;
    }

    form {
      display: flex;
      flex-direction: column;
      width: 100%;
      padding-top: 4px;
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 16px 0 12px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.12);
      color: #1976d2;
      font-weight: 500;
      font-size: 14px;
    }

    .section-header:first-child {
      margin-top: 0;
    }

    .section-header mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .checkbox-field {
      margin-bottom: 16px;
    }
  `]
})
export class WorkflowFormDialogComponent implements OnInit {
  private dialogRef = inject(MatDialogRef<WorkflowFormDialogComponent>);
  private data = inject(MAT_DIALOG_DATA);
  private apiService = inject(ApiService);

  ConversationPattern = ConversationPattern;

  workflow: WorkflowConfig;
  isEdit = signal(false);
  availableAgents = signal<AgentConfig[]>([]);

  // Group chat specific fields
  groupAgents: string[] = [];
  groupMaxRound: number = 10;
  groupSpeakerMethod: string = 'auto';

  constructor() {
    if (this.data.workflow) {
      this.workflow = { ...this.data.workflow };
      this.isEdit.set(true);
      
      // Extract group chat settings if present
      if (this.workflow.group_chat) {
        this.groupAgents = this.workflow.group_chat.agents || [];
        this.groupMaxRound = this.workflow.group_chat.max_round || 10;
        this.groupSpeakerMethod = this.workflow.group_chat.speaker_selection_method || 'auto';
      }
    } else {
      // Initialize with all required defaults
      this.workflow = {
        id: '',
        name: '',
        description: '',
        pattern: ConversationPattern.TWO_AGENT,
        entry_agent_id: '',
        recipient_agent_id: '',
        max_turns: 10,
        summary_method: 'last_msg',
        enabled: true,
        workflow_type: 'sequential',
        persistence: 'postgres',
        metadata: {}
      };
    }
  }

  ngOnInit(): void {
    this.loadAgents();
  }

  loadAgents(): void {
    this.apiService.getAgents().subscribe({
      next: (agents) => {
        this.availableAgents.set(agents);
      },
      error: (err) => {
        console.error('Error loading agents:', err);
      }
    });
  }

  isValid(): boolean {
    if (!this.workflow.id || !this.workflow.name || !this.workflow.entry_agent_id) {
      return false;
    }
    
    if (this.workflow.pattern === ConversationPattern.TWO_AGENT) {
      return !!this.workflow.recipient_agent_id;
    }
    
    if (this.workflow.pattern === ConversationPattern.GROUP_CHAT) {
      return this.groupAgents.length >= 2;
    }
    
    return true;
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    // Build group_chat config if needed
    if (this.workflow.pattern === ConversationPattern.GROUP_CHAT) {
      this.workflow.group_chat = {
        agents: this.groupAgents,
        max_round: this.groupMaxRound,
        speaker_selection_method: this.groupSpeakerMethod,
        send_introductions: false
      };
    }
    
    // Ensure all required fields have values
    if (!this.workflow.max_turns) {
      this.workflow.max_turns = 10;
    }
    if (!this.workflow.summary_method) {
      this.workflow.summary_method = 'last_msg';
    }
    if (this.workflow.enabled === undefined) {
      this.workflow.enabled = true;
    }
    if (!this.workflow.workflow_type) {
      this.workflow.workflow_type = 'sequential';
    }
    if (!this.workflow.persistence) {
      this.workflow.persistence = 'postgres';
    }
    
    this.dialogRef.close(this.workflow);
  }
}
