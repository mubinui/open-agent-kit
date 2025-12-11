import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSliderModule } from '@angular/material/slider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AgentConfig, AgentType, HumanInputMode, LLMConfig, RetrieveConfig, AgentBehaviorConfig } from '../../models/agent.model';
import { ApiService, ApiProvider, ApiProviderModel } from '../../services/api.service';
import { ToolConfig } from '../../models/tool.model';

@Component({
  selector: 'app-agent-form-dialog',
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
    MatSliderModule,
    MatExpansionModule,
    MatIconModule,
    MatTooltipModule
  ],
  template: `
    <h2 mat-dialog-title>{{ isEdit() ? 'Edit Agent' : 'Create Agent' }}</h2>
    <mat-dialog-content>
      <form>
        <!-- Basic Info Section -->
        <div class="section-header">
          <mat-icon>info</mat-icon>
          <span>Basic Information</span>
        </div>
        
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>ID</mat-label>
          <input matInput [(ngModel)]="agent.id" name="id" required [disabled]="isEdit()"
                 pattern="^[a-z0-9_]+$">
          <mat-hint>Lowercase letters, numbers, and underscores only</mat-hint>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Name</mat-label>
          <input matInput [(ngModel)]="agent.name" name="name" required
                 (ngModelChange)="sanitizeName($event)">
          <mat-hint>No spaces allowed (System requirement)</mat-hint>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Type</mat-label>
          <mat-select [(ngModel)]="agent.type" name="type" required>
            <mat-option [value]="AgentType.CONVERSABLE">Conversable</mat-option>
            <mat-option [value]="AgentType.RETRIEVE_USER_PROXY">Retrieve User Proxy</mat-option>
            <mat-option [value]="AgentType.GROUP_CHAT_MANAGER">Group Chat Manager</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>System Message</mat-label>
          <textarea matInput [(ngModel)]="agent.system_message" name="system_message" rows="3"></textarea>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Description</mat-label>
          <textarea matInput [(ngModel)]="agent.description" name="description" rows="2"></textarea>
        </mat-form-field>

        <!-- Retrieval Configuration Section (Only for Retrieve User Proxy) -->
        <div *ngIf="agent.type === AgentType.RETRIEVE_USER_PROXY" class="config-section">
          <div class="section-header">
            <mat-icon>find_in_page</mat-icon>
            <span>Retrieval Configuration</span>
          </div>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Task</mat-label>
            <mat-select [(ngModel)]="retrieveConfig.task" name="retrieve_task">
              <mat-option value="qa">QA</mat-option>
              <mat-option value="code">Code</mat-option>
              <mat-option value="default">Default</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Docs Path (comma separated)</mat-label>
            <input matInput [ngModel]="docsPathString" (ngModelChange)="updateDocsPath($event)" name="docs_path" required>
            <mat-hint>Paths or URLs to index</mat-hint>
          </mat-form-field>

          <div class="row">
            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Vector DB</mat-label>
              <input matInput [(ngModel)]="retrieveConfig.vector_db" name="vector_db">
            </mat-form-field>

            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Collection Name</mat-label>
              <input matInput [(ngModel)]="retrieveConfig.collection_name" name="collection_name">
            </mat-form-field>
          </div>
          
           <div class="row">
            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Chunk Token Size</mat-label>
              <input matInput type="number" [(ngModel)]="retrieveConfig.chunk_token_size" name="chunk_token_size">
            </mat-form-field>

            <mat-checkbox [(ngModel)]="retrieveConfig.get_or_create" name="get_or_create">
              Get/Create Collection
            </mat-checkbox>
          </div>
        </div>

        <!-- LLM Configuration Section -->
        <div class="section-header">
          <mat-icon>smart_toy</mat-icon>
          <span>LLM Configuration</span>
          <mat-icon class="info-icon" matTooltip="Configure the language model for this agent">help_outline</mat-icon>
        </div>

        <div class="llm-config-section">
          <div class="row">
            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Provider</mat-label>
              <mat-select [(ngModel)]="llmConfig.provider_id" name="provider_id" (selectionChange)="onProviderChange()">
                <mat-option *ngFor="let provider of llmProviders()" [value]="provider.id">
                  {{ provider.name }}
                </mat-option>
              </mat-select>
              <mat-hint>Select LLM provider</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="half-width">
              <mat-label>Model</mat-label>
              <mat-select [(ngModel)]="llmConfig.model" name="model">
                <mat-option *ngFor="let model of availableModels()" [value]="model.name">
                  {{ model.name }}
                  <span *ngIf="model.default" class="default-badge">default</span>
                </mat-option>
              </mat-select>
              <mat-hint>Select model from provider</mat-hint>
            </mat-form-field>
          </div>

          <div class="row">
            <mat-form-field appearance="outline" class="third-width">
              <mat-label>Temperature</mat-label>
              <input matInput type="number" [(ngModel)]="llmConfig.temperature" name="temperature" 
                     min="0" max="2" step="0.1">
              <mat-hint>0 = focused, 2 = creative</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="third-width">
              <mat-label>Max Tokens</mat-label>
              <input matInput type="number" [(ngModel)]="llmConfig.max_tokens" name="max_tokens" 
                     min="100" max="128000">
              <mat-hint>Maximum response length</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="third-width">
              <mat-label>Timeout (s)</mat-label>
              <input matInput type="number" [(ngModel)]="llmConfig.timeout" name="timeout" 
                     min="10" max="600">
              <mat-hint>Request timeout in seconds</mat-hint>
            </mat-form-field>
          </div>

          <mat-form-field appearance="outline" class="half-width">
            <mat-label>Cache Seed</mat-label>
            <input matInput type="number" [(ngModel)]="llmConfig.cache_seed" name="cache_seed">
            <mat-hint>Optional: for deterministic responses</mat-hint>
          </mat-form-field>
        </div>

        <!-- Behavior Section -->
        <div class="section-header">
          <mat-icon>settings</mat-icon>
          <span>Behavior Settings</span>
        </div>

        <mat-form-field appearance="outline" class="full-width">
            <mat-label>Output Format</mat-label>
            <input matInput [(ngModel)]="behaviorConfig.output_format" name="output_format" placeholder="e.g. JSON, XML">
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Human Input Mode</mat-label>
          <mat-select [(ngModel)]="agent.human_input_mode" name="human_input_mode" required>
            <mat-option [value]="HumanInputMode.ALWAYS">Always</mat-option>
            <mat-option [value]="HumanInputMode.NEVER">Never</mat-option>
            <mat-option [value]="HumanInputMode.TERMINATE">Terminate</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Max Consecutive Auto Reply</mat-label>
          <input matInput type="number" [(ngModel)]="agent.max_consecutive_auto_reply" name="max_consecutive_auto_reply" required min="1">
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Tools</mat-label>
          <mat-select [(ngModel)]="agent.tools" name="tools" multiple>
            <mat-option *ngFor="let tool of availableTools()" [value]="tool.id">
              {{ tool.name }}
            </mat-option>
          </mat-select>
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" (click)="onSave()">Save</button>
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
        background: transparent;
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

    .third-width {
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

    .info-icon {
      margin-left: auto;
      color: #666;
      cursor: help;
      font-size: 18px !important;
      width: 18px !important;
      height: 18px !important;
    }

    .llm-config-section {
      background: #f8f9fa;
      padding: 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .default-badge {
      background: #4caf50;
      color: white;
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 10px;
      margin-left: 8px;
    }
  `]
})
export class AgentFormDialogComponent implements OnInit {
  private dialogRef = inject(MatDialogRef<AgentFormDialogComponent>);
  private data = inject(MAT_DIALOG_DATA);
  private apiService = inject(ApiService);

  AgentType = AgentType;
  HumanInputMode = HumanInputMode;

  agent: AgentConfig;

  retrieveConfig: RetrieveConfig = {
    task: 'qa',
    docs_path: [],
    chunk_token_size: 2000,
    vector_db: 'chromadb',
    collection_name: 'autogen_docs',
    embedding_model: 'all-mpnet-base-v2',
    get_or_create: true
  };

  behaviorConfig: AgentBehaviorConfig = {};

  docsPathString = '';

  isEdit = signal(false);
  availableTools = signal<ToolConfig[]>([]);
  llmProviders = signal<ApiProvider[]>([]);
  availableModels = signal<ApiProviderModel[]>([]);

  llmConfig: LLMConfig = {
    provider_id: '',
    model: '',
    temperature: 0.7,
    max_tokens: 1000,
    timeout: 120,
    cache_seed: 42
  };

  constructor() {
    if (this.data.agent) {
      this.agent = { ...this.data.agent };
      // Load existing LLM config if present
      if (this.agent.llm_config && typeof (this.agent.llm_config) !== 'boolean') {
        const config = this.agent.llm_config as LLMConfig;
        this.llmConfig = { ...config };
      }
      if (this.agent.retrieve_config) {
        this.retrieveConfig = { ...this.agent.retrieve_config };
        this.docsPathString = this.retrieveConfig.docs_path.join(', ');
      }
      if (this.agent.behavior) {
        this.behaviorConfig = { ...this.agent.behavior };
      }
      this.isEdit.set(true);
    } else {
      this.agent = {
        id: '',
        type: AgentType.CONVERSABLE,
        name: '',
        human_input_mode: HumanInputMode.NEVER,
        tools: [],
        max_consecutive_auto_reply: 10
      };
    }
  }

  ngOnInit(): void {
    this.loadTools();
    this.loadProviders();
  }

  loadTools(): void {
    this.apiService.getTools().subscribe({
      next: (tools) => {
        this.availableTools.set(tools);
      },
      error: (err) => {
        console.error('Error loading tools:', err);
      }
    });
  }

  loadProviders(): void {
    this.apiService.getApiProviders().subscribe({
      next: (providers) => {
        // Filter to only LLM type providers
        const llmProviders = providers.filter(p => p.type === 'llm');
        this.llmProviders.set(llmProviders);

        // Set available models based on current provider
        this.updateAvailableModels();
      },
      error: (err) => {
        console.error('Error loading providers:', err);
        // Fallback to default provider
        this.llmProviders.set([{
          id: 'openrouter',
          name: 'OpenRouter',
          type: 'llm',
          models: [{ name: '@preset/procurement-chatbot', default: true }]
        }]);
        this.updateAvailableModels();
      }
    });
  }

  onProviderChange(): void {
    this.updateAvailableModels();
    // Reset model selection when provider changes
    const models = this.availableModels();
    if (models.length > 0) {
      const defaultModel = models.find(m => m.default) || models[0];
      this.llmConfig.model = defaultModel.name;
    }
  }

  updateAvailableModels(): void {
    const provider = this.llmProviders().find(p => p.id === this.llmConfig.provider_id);
    if (provider && provider.models) {
      this.availableModels.set(provider.models);
    } else {
      this.availableModels.set([]);
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  sanitizeName(value: string): void {
    if (!value) return;
    // Remove spaces from agent name (Autogen requirement)
    this.agent.name = value.replace(/\s+/g, '');
  }

  updateDocsPath(value: string): void {
    this.docsPathString = value;
    this.retrieveConfig.docs_path = value.split(',').map(s => s.trim()).filter(s => s.length > 0);
  }

  onSave(): void {
    // Ensure name has no spaces
    if (this.agent.name) {
      this.agent.name = this.agent.name.replace(/\s+/g, '');
    }

    // Attach LLM config to agent before saving
    this.agent.llm_config = { ...this.llmConfig };

    // Set code_execution_config to false by default
    if (this.agent.code_execution_config === undefined) {
      this.agent.code_execution_config = false;
    }

    if (this.agent.type === AgentType.RETRIEVE_USER_PROXY) {
      this.agent.retrieve_config = { ...this.retrieveConfig };
    } else {
      delete this.agent.retrieve_config;
    }

    // Add behavior config if fields are set
    if (Object.keys(this.behaviorConfig).length > 0) {
      this.agent.behavior = { ...this.behaviorConfig };
    }

    this.dialogRef.close(this.agent);
  }
}
