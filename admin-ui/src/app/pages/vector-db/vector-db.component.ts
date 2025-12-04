import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatListModule } from '@angular/material/list';
import { ApiService, VectorDbConfig, RagCollections } from '../../services/api.service';

@Component({
  selector: 'app-vector-db',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDividerModule,
    MatListModule
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
                    <mat-icon>storage</mat-icon>
                    <div>
                      <strong>Vector DB</strong>
                      <span>{{ ragService.health_details['vector_db']?.type || 'N/A' }}</span>
                    </div>
                  </div>
                  <div class="health-item">
                    <mat-icon>blur_on</mat-icon>
                    <div>
                      <strong>Embedding Service</strong>
                      <span>{{ ragService.health_details['embedding_service']?.model || 'N/A' }}</span>
                    </div>
                  </div>
                  <div class="health-item">
                    <mat-icon>sort</mat-icon>
                    <div>
                      <strong>Reranker Service</strong>
                      <span>{{ ragService.health_details['reranker_service']?.model || 'N/A' }}</span>
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
              <mat-card-title>Integration Guide</mat-card-title>
              <mat-card-subtitle>How to use RAG service in workflows</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <h3>Available RAG Tools</h3>
              <ul class="tool-list">
                <li><code>rag_query</code> - Query documents with semantic search</li>
                <li><code>rag_ingest_file</code> - Upload documents for indexing</li>
                <li><code>rag_list_files</code> - List ingested documents</li>
                <li><code>rag_delete_file</code> - Remove documents from collection</li>
                <li><code>rag_get_stats</code> - Get collection statistics</li>
              </ul>
              
              <h3>Example Workflows</h3>
              <ul class="tool-list">
                <li><strong>rag_qa_assistant</strong> - Simple Q&A using RAG</li>
                <li><strong>rag_research_workflow</strong> - Multi-step research with reasoning</li>
              </ul>
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
      align-items: center;
      gap: 12px;
    }
    .health-item mat-icon {
      color: #64748b;
    }
    .health-item div {
      display: flex;
      flex-direction: column;
    }
    .health-item span {
      font-size: 14px;
      color: #64748b;
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
  
  ragService: VectorDbConfig | null = null;
  collections: RagCollections | null = null;
  loading = true;
  loadingCollections = false;
  error: string | null = null;

  ngOnInit() {
    this.loadRagService();
  }

  loadRagService() {
    this.loading = true;
    this.error = null;
    
    this.apiService.getRagService().subscribe({
      next: (service) => {
        this.ragService = service;
        this.loading = false;
        this.loadCollections();
      },
      error: (err) => {
        console.error('Failed to load RAG service', err);
        this.error = 'Failed to load RAG service configuration. Please check if the backend service is running.';
        this.loading = false;
      }
    });
  }

  loadCollections() {
    this.loadingCollections = true;
    this.apiService.getRagCollections().subscribe({
      next: (collections) => {
        this.collections = collections;
        this.loadingCollections = false;
      },
      error: (err) => {
        console.error('Failed to load collections', err);
        this.loadingCollections = false;
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
