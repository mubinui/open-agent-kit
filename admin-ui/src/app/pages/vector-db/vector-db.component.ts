import { Component, OnInit, inject, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatListModule } from '@angular/material/list';
import { MatExpansionModule } from '@angular/material/expansion';
import { ApiService, VectorDbConfig, RagCollections } from '../../services/api.service';
import { ToolConfig } from '../../models/tool.model';

@Component({
  selector: 'app-vector-db',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDividerModule,
    MatListModule,
    MatExpansionModule
  ],
  template: `
    <div class="container">
      <div class="header">
        <h1>RAG Service</h1>
        <p class="subtitle">Remote RAG Pipeline for document retrieval and semantic search</p>
      </div>

      @if (loading) {
        <div class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (error) {
        <div class="error-container">
          <mat-icon color="warn">error</mat-icon>
          <p>{{ error }}</p>
          <button mat-raised-button color="primary" (click)="loadRagService()">
            <mat-icon>refresh</mat-icon>
            Retry
          </button>
        </div>
      } @else if (ragService) {
        <div class="service-container">
          <!-- Service Status Card -->
          <mat-card class="status-card">
            <mat-card-header>
              <mat-icon mat-card-avatar [class.healthy]="ragService.health_status === 'healthy'" 
                        [class.unhealthy]="ragService.health_status !== 'healthy'">
                {{ getHealthIcon() }}
              </mat-icon>
              <mat-card-title>Service Status</mat-card-title>
              <mat-card-subtitle>{{ ragService.base_url }}</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <div class="status-grid">
                <div class="status-item">
                  <span class="label">Status</span>
                  <mat-chip [class.chip-healthy]="ragService.health_status === 'healthy'"
                            [class.chip-unhealthy]="ragService.health_status !== 'healthy'">
                    {{ ragService.health_status || 'Unknown' }}
                  </mat-chip>
                </div>
                <div class="status-item">
                  <span class="label">Type</span>
                  <span class="value">{{ ragService.type }}</span>
                </div>
                <div class="status-item">
                  <span class="label">Default Collection</span>
                  <span class="value">{{ ragService.default_collection }}</span>
                </div>
                <div class="status-item">
                  <span class="label">Timeout</span>
                  <span class="value">{{ ragService.timeout }}s</span>
                </div>
              </div>
              
              @if (ragService.health_details) {
                <mat-divider class="divider"></mat-divider>
                <h3>Health Details</h3>
                <div class="health-details">
                  <div class="health-item">
                    <mat-icon [class.healthy]="ragService.health_details['vector_db']?.status === 'healthy'"
                              [class.unhealthy]="ragService.health_details['vector_db']?.status !== 'healthy'">
                      storage
                    </mat-icon>
                    <div>
                      <strong>Vector DB</strong>
                      <span>{{ ragService.health_details['vector_db']?.type || 'N/A' }}</span>
                      <mat-chip size="small"
                                [class.chip-healthy]="ragService.health_details['vector_db']?.status === 'healthy'"
                                [class.chip-unhealthy]="ragService.health_details['vector_db']?.status !== 'healthy'">
                        {{ ragService.health_details['vector_db']?.status || 'unknown' }}
                      </mat-chip>
                      @if (ragService.health_details['vector_db']?.error) {
                        <span class="error-text">{{ ragService.health_details['vector_db']?.error }}</span>
                      }
                    </div>
                  </div>
                  <div class="health-item">
                    <mat-icon [class.healthy]="ragService.health_details['embedding_service']?.status === 'healthy'"
                              [class.unhealthy]="ragService.health_details['embedding_service']?.status !== 'healthy'">
                      blur_on
                    </mat-icon>
                    <div>
                      <strong>Embedding Service</strong>
                      <span>{{ ragService.health_details['embedding_service']?.model || 'N/A' }}</span>
                      <mat-chip size="small"
                                [class.chip-healthy]="ragService.health_details['embedding_service']?.status === 'healthy'"
                                [class.chip-unhealthy]="ragService.health_details['embedding_service']?.status !== 'healthy'">
                        {{ ragService.health_details['embedding_service']?.status || 'unknown' }}
                      </mat-chip>
                      @if (ragService.health_details['embedding_service']?.error) {
                        <span class="error-text">{{ ragService.health_details['embedding_service']?.error }}</span>
                      }
                    </div>
                  </div>
                  <div class="health-item">
                    <mat-icon [class.healthy]="ragService.health_details['reranker_service']?.status === 'healthy'"
                              [class.unhealthy]="ragService.health_details['reranker_service']?.status !== 'healthy'">
                      sort
                    </mat-icon>
                    <div>
                      <strong>Reranker Service</strong>
                      <span>{{ ragService.health_details['reranker_service']?.model || 'N/A' }}</span>
                      <mat-chip size="small"
                                [class.chip-healthy]="ragService.health_details['reranker_service']?.status === 'healthy'"
                                [class.chip-unhealthy]="ragService.health_details['reranker_service']?.status !== 'healthy'">
                        {{ ragService.health_details['reranker_service']?.status || 'unknown' }}
                      </mat-chip>
                      @if (ragService.health_details['reranker_service']?.error) {
                        <span class="error-text">{{ ragService.health_details['reranker_service']?.error }}</span>
                      }
                    </div>
                  </div>
                </div>
              }
            </mat-card-content>
            <mat-card-actions align="end">
              <button mat-button color="primary" (click)="loadRagService()">
                <mat-icon>refresh</mat-icon>
                Refresh Status
              </button>
              <button mat-button (click)="openSwagger()">
                <mat-icon>api</mat-icon>
                API Docs
              </button>
            </mat-card-actions>
          </mat-card>

          <!-- Collections Card -->
          <mat-card class="collections-card">
            <mat-card-header>
              <mat-icon mat-card-avatar>folder</mat-icon>
              <mat-card-title>Available Collections</mat-card-title>
              <mat-card-subtitle>Document collections in RAG service</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              @if (loadingCollections) {
                <div class="loading-small">
                  <mat-spinner diameter="30"></mat-spinner>
                </div>
              } @else if (collections && collections.collections.length > 0) {
                <mat-list>
                  @for (collection of collections.collections; track collection) {
                    <mat-list-item>
                      <mat-icon matListItemIcon>description</mat-icon>
                      <span matListItemTitle>{{ collection }}</span>
                    </mat-list-item>
                  }
                </mat-list>
                <p class="collection-count">Total: {{ collections.total }} collections</p>
              } @else {
                <p class="no-data">No collections available</p>
              }
            </mat-card-content>
          </mat-card>

          <!-- Integration Guide Card -->
          <mat-card class="guide-card">
            <mat-card-header>
              <mat-icon mat-card-avatar>integration_instructions</mat-icon>
              <mat-card-title>Available RAG Tools</mat-card-title>
              <mat-card-subtitle>Tools available for agents to interact with RAG service</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              @if (loadingTools) {
                <div class="loading-small">
                  <mat-spinner diameter="30"></mat-spinner>
                </div>
              } @else if (ragTools.length > 0) {
                <mat-accordion>
                  @for (tool of ragTools; track tool.id) {
                    <mat-expansion-panel>
                      <mat-expansion-panel-header>
                        <mat-panel-title>
                          <code>{{ tool.name }}</code>
                        </mat-panel-title>
                        <mat-panel-description>
                          {{ tool.description | slice:0:60 }}{{ tool.description.length > 60 ? '...' : '' }}
                        </mat-panel-description>
                      </mat-expansion-panel-header>
                      
                      <div class="tool-details">
                        <p><strong>Description:</strong> {{ tool.description }}</p>
                        <p><strong>ID:</strong> <code>{{ tool.id }}</code></p>
                        <p><strong>Entrypoint:</strong> <code>{{ tool.entrypoint }}</code></p>
                        
                        @if (tool.settings && Object.keys(tool.settings).length > 0) {
                          <div class="settings-section">
                            <strong>Settings:</strong>
                            <pre>{{ tool.settings | json }}</pre>
                          </div>
                        }
                      </div>
                    </mat-expansion-panel>
                  }
                </mat-accordion>
              } @else {
                <p class="no-data">No RAG tools found. Check tools configuration.</p>
              }
              
              <div class="example-workflows">
                <h3>Example Workflows</h3>
                <ul class="tool-list">
                  <li><strong>rag_qa_assistant</strong> - Simple Q&A using RAG</li>
                  <li><strong>rag_research_workflow</strong> - Multi-step research with reasoning</li>
                </ul>
              </div>
            </mat-card-content>
          </mat-card>
        </div>
      }
    </div>
  `,
  styles: [`
    .container {
      padding: 24px;
      max-width: 1400px;
      margin: 0 auto;
    }
    .header {
      margin-bottom: 32px;
    }
    .header h1 {
      margin: 0 0 8px 0;
      color: #1e293b;
    }
    .subtitle {
      color: #64748b;
      margin: 0;
    }
    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }
    .loading-small {
      display: flex;
      justify-content: center;
      padding: 24px;
    }
    .error-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      gap: 16px;
    }
    .error-container mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }
    .service-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .status-card {
      grid-column: 1 / -1;
    }
    mat-card {
      height: 100%;
    }
    mat-card-avatar {
      font-size: 40px;
      width: 40px;
      height: 40px;
    }
    mat-card-avatar.healthy {
      color: #10b981;
    }
    mat-card-avatar.unhealthy {
      color: #ef4444;
    }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }
    .status-item {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .status-item .label {
      font-size: 12px;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .status-item .value {
      font-size: 16px;
      font-weight: 500;
      color: #1e293b;
    }
    .chip-healthy {
      background-color: #10b981 !important;
      color: white !important;
    }
    .chip-unhealthy {
      background-color: #ef4444 !important;
      color: white !important;
    }
    .divider {
      margin: 24px 0;
    }
    h3 {
      margin: 16px 0 12px 0;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
    }
    .health-details {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .health-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }
    .health-item mat-icon {
      color: #64748b;
      margin-top: 2px;
    }
    .health-item mat-icon.healthy {
      color: #10b981;
    }
    .health-item mat-icon.unhealthy {
      color: #ef4444;
    }
    .health-item div {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .health-item span {
      font-size: 14px;
      color: #64748b;
    }
    .health-item .error-text {
      font-size: 12px;
      color: #ef4444;
      background: #fef2f2;
      padding: 4px 8px;
      border-radius: 4px;
      margin-top: 4px;
    }
    .chip-healthy {
      background-color: #d1fae5 !important;
      color: #065f46 !important;
    }
    .chip-unhealthy {
      background-color: #fee2e2 !important;
      color: #991b1b !important;
    }
    .collection-count {
      margin-top: 16px;
      font-size: 14px;
      color: #64748b;
      text-align: center;
    }
    .no-data {
      text-align: center;
      color: #64748b;
      padding: 24px;
    }
    .tool-list {
      margin: 12px 0;
      padding-left: 20px;
    }
    .tool-list li {
      margin: 8px 0;
      line-height: 1.6;
    }
    .tool-details {
      padding: 16px 0;
    }
    .tool-details p {
      margin: 8px 0;
    }
    .settings-section {
      margin-top: 12px;
    }
    .settings-section pre {
      background: #f8fafc;
      padding: 12px;
      border-radius: 4px;
      font-size: 12px;
      margin-top: 4px;
      overflow-x: auto;
    }
    .example-workflows {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;
    }
    code {
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: monospace;
      color: #D91B5C;
    }
  `]
})
export class VectorDbComponent implements OnInit {
  private apiService = inject(ApiService);
  private cdr = inject(ChangeDetectorRef);
  
  ragService: VectorDbConfig | null = null;
  collections: RagCollections | null = null;
  ragTools: ToolConfig[] = [];
  loading = true;
  loadingCollections = false;
  loadingTools = false;
  error: string | null = null;
  
  // Helper for template
  Object = Object;

  ngOnInit() {
    this.loadRagService();
    this.loadRagTools();
  }

  loadRagService() {
    this.loading = true;
    this.error = null;
    
    this.apiService.getRagService().subscribe({
      next: (service) => {
        this.ragService = service;
        this.loading = false;
        this.loadCollections();
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load RAG service', err);
        this.error = 'Failed to load RAG service configuration. Please check if the backend service is running.';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  loadCollections() {
    this.loadingCollections = true;
    this.apiService.getRagCollections().subscribe({
      next: (collections) => {
        this.collections = collections;
        this.loadingCollections = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load collections', err);
        this.loadingCollections = false;
        this.cdr.markForCheck();
      }
    });
  }

  loadRagTools() {
    this.loadingTools = true;
    this.apiService.getTools().subscribe({
      next: (tools) => {
        this.ragTools = tools.filter(t => t.id.startsWith('rag_'));
        this.loadingTools = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load tools', err);
        this.loadingTools = false;
        this.cdr.markForCheck();
      }
    });
  }

  getHealthIcon(): string {
    if (!this.ragService) return 'help';
    
    switch (this.ragService.health_status) {
      case 'healthy':
        return 'check_circle';
      case 'unhealthy':
      case 'degraded':
        return 'warning';
      case 'unreachable':
        return 'cloud_off';
      default:
        return 'help';
    }
  }

  openSwagger() {
    if (this.ragService) {
      window.open(`${this.ragService.base_url}/docs`, '_blank');
    }
  }
}
