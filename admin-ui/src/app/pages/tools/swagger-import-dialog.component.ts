import { Component, inject, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatStepperModule, MatStepper } from '@angular/material/stepper';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HttpErrorResponse } from '@angular/common/http';
import { 
  ApiService, 
  SwaggerPreviewResponse, 
  SwaggerImportResult 
} from '../../services/api.service';

@Component({
  selector: 'app-swagger-import-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatChipsModule,
    MatIconModule,
    MatStepperModule,
    MatTooltipModule
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>cloud_download</mat-icon>
      Import Tools from Swagger/OpenAPI
    </h2>
    
    <mat-dialog-content>
      <mat-stepper [linear]="true" #stepper>
        <!-- Step 1: Enter URL -->
        <mat-step [completed]="previewLoaded()">
          <ng-template matStepLabel>Enter Swagger URL</ng-template>
          
          <div class="step-content">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Swagger/OpenAPI URL</mat-label>
              <input matInput [(ngModel)]="swaggerUrl" 
                     placeholder="https://api.example.com/swagger.json"
                     [disabled]="loading()">
              <mat-hint>Supports OpenAPI 2.0 (Swagger) and 3.0+ specifications (JSON or YAML)</mat-hint>
            </mat-form-field>
            
            @if (previewError()) {
              <div class="error-message">
                <mat-icon>error</mat-icon>
                {{ previewError() }}
              </div>
            }
            
            <div class="step-actions">
              <button mat-raised-button (click)="close()">Cancel</button>
              <button mat-raised-button color="primary" 
                      (click)="loadPreview()"
                      [disabled]="!swaggerUrl || loading()"
                      class="action-button">
                @if (loading()) {
                  <mat-spinner diameter="18" class="button-spinner"></mat-spinner>
                  <span>Loading...</span>
                } @else {
                  <ng-container>
                    <mat-icon>search</mat-icon>
                    <span>Preview Endpoints</span>
                  </ng-container>
                }
              </button>
            </div>
          </div>
        </mat-step>
        
        <!-- Step 2: Select Endpoints -->
        <mat-step [completed]="!!importResult()">
          <ng-template matStepLabel>Select Endpoints</ng-template>
          
          <div class="step-content">
            @if (preview()) {
              <div class="api-info">
                <h3>{{ preview()!.title }} <span class="version">v{{ preview()!.version }}</span></h3>
                <p class="description">{{ preview()!.description }}</p>
                <div class="meta">
                  <mat-chip>OpenAPI {{ preview()!.openapi_version }}</mat-chip>
                  <mat-chip>Base: {{ preview()!.base_url }}</mat-chip>
                  <mat-chip>{{ preview()!.total_endpoints }} endpoints</mat-chip>
                  @if (preview()!.duplicate_count > 0) {
                    <mat-chip class="warning">{{ preview()!.duplicate_count }} duplicates</mat-chip>
                  }
                </div>
              </div>
              
              <div class="selection-controls">
                <button mat-button (click)="selectAll()">Select All</button>
                <button mat-button (click)="deselectAll()">Deselect All</button>
                <button mat-button (click)="selectNonDuplicates()">Select Non-Duplicates</button>
                <span class="selection-count">{{ selectedCount() }} selected</span>
              </div>
              
              <div class="endpoints-table-container">
                <table mat-table [dataSource]="preview()!.endpoints" class="endpoints-table">
                  <!-- Checkbox Column -->
                  <ng-container matColumnDef="select">
                    <th mat-header-cell *matHeaderCellDef></th>
                    <td mat-cell *matCellDef="let endpoint">
                      <mat-checkbox [(ngModel)]="selectedEndpoints[endpoint.operation_id]"
                                    [disabled]="endpoint.is_duplicate"
                                    [matTooltip]="endpoint.is_duplicate ? 'Tool ID already exists' : ''">
                      </mat-checkbox>
                    </td>
                  </ng-container>
                  
                  <!-- Method Column -->
                  <ng-container matColumnDef="method">
                    <th mat-header-cell *matHeaderCellDef>Method</th>
                    <td mat-cell *matCellDef="let endpoint">
                      <mat-chip [class]="'method-' + endpoint.method.toLowerCase()">
                        {{ endpoint.method }}
                      </mat-chip>
                    </td>
                  </ng-container>
                  
                  <!-- Path Column -->
                  <ng-container matColumnDef="path">
                    <th mat-header-cell *matHeaderCellDef>Path</th>
                    <td mat-cell *matCellDef="let endpoint">{{ endpoint.path }}</td>
                  </ng-container>
                  
                  <!-- Summary Column -->
                  <ng-container matColumnDef="summary">
                    <th mat-header-cell *matHeaderCellDef>Summary</th>
                    <td mat-cell *matCellDef="let endpoint">{{ endpoint.summary || endpoint.operation_id }}</td>
                  </ng-container>
                  
                  <!-- Tool ID Column -->
                  <ng-container matColumnDef="tool_id">
                    <th mat-header-cell *matHeaderCellDef>Tool ID</th>
                    <td mat-cell *matCellDef="let endpoint">
                      <code [class.duplicate]="endpoint.is_duplicate">{{ endpoint.generated_tool_id }}</code>
                      @if (endpoint.is_duplicate) {
                        <mat-icon class="duplicate-icon" matTooltip="Duplicate - tool ID already exists">warning</mat-icon>
                      }
                    </td>
                  </ng-container>
                  
                  <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                  <tr mat-row *matRowDef="let row; columns: displayedColumns;" 
                      [class.duplicate-row]="row.is_duplicate"></tr>
                </table>
              </div>
              
              <!-- Import Options -->
              <div class="import-options">
                <h4>Import Options</h4>
                
                <mat-form-field appearance="outline" class="half-width">
                  <mat-label>Authentication Type</mat-label>
                  <mat-select [(ngModel)]="importOptions.auth_type">
                    <mat-option value="none">None</mat-option>
                    <mat-option value="bearer">Bearer Token</mat-option>
                    <mat-option value="api_key">API Key</mat-option>
                    <mat-option value="basic">Basic Auth</mat-option>
                  </mat-select>
                </mat-form-field>
                
                @if (importOptions.auth_type !== 'none') {
                  <mat-form-field appearance="outline" class="half-width">
                    <mat-label>Auth Environment Variable</mat-label>
                    <input matInput [(ngModel)]="importOptions.auth_env_var"
                           placeholder="MY_API_KEY">
                    <mat-hint>Environment variable containing auth credentials</mat-hint>
                  </mat-form-field>
                }
                
                <mat-form-field appearance="outline" class="half-width">
                  <mat-label>Timeout (seconds)</mat-label>
                  <input matInput type="number" [(ngModel)]="importOptions.timeout"
                         min="1" max="300">
                </mat-form-field>
                
                <div class="checkbox-options">
                  <mat-checkbox [(ngModel)]="importOptions.forward_user_context">
                    Forward User Context Headers (x-client-username, x-client-ref)
                  </mat-checkbox>
                  
                  <mat-checkbox [(ngModel)]="importOptions.enabled">
                    Enable imported tools immediately
                  </mat-checkbox>
                </div>
              </div>
            }
            
            @if (importError()) {
              <div class="error-message">
                <mat-icon>error</mat-icon>
                {{ importError() }}
              </div>
            }
            
            <div class="step-actions">
              <button mat-raised-button (click)="close()">Cancel</button>
              <button mat-button matStepperPrevious>Back</button>
              <button mat-raised-button color="primary" 
                      (click)="importTools()"
                      [disabled]="selectedCount() === 0 || importing()"
                      class="action-button">
                @if (importing()) {
                  <mat-spinner diameter="18" class="button-spinner"></mat-spinner>
                  <span>Importing...</span>
                } @else {
                  <ng-container>
                    <mat-icon>download</mat-icon>
                    <span>Import {{ selectedCount() }} Tools</span>
                  </ng-container>
                }
              </button>
            </div>
          </div>
        </mat-step>
        
        <!-- Step 3: Results -->
        <mat-step>
          <ng-template matStepLabel>Import Results</ng-template>
          
          <div class="step-content">
            @if (importResult()) {
              <div class="results">
                @if (importResult()!.success) {
                  <div class="success-message">
                    <mat-icon>check_circle</mat-icon>
                    Successfully imported {{ importResult()!.imported_count }} tools
                  </div>
                } @else {
                  <div class="error-message">
                    <mat-icon>error</mat-icon>
                    Import failed
                  </div>
                }
                
                @if (importResult()!.imported_tools.length > 0) {
                  <div class="result-section">
                    <h4>Imported Tools</h4>
                    <div class="tool-list">
                      @for (tool of importResult()!.imported_tools; track tool) {
                        <mat-chip class="success-chip">{{ tool }}</mat-chip>
                      }
                    </div>
                  </div>
                }
                
                @if (importResult()!.skipped_duplicates.length > 0) {
                  <div class="result-section">
                    <h4>Skipped (Duplicates)</h4>
                    <div class="tool-list">
                      @for (tool of importResult()!.skipped_duplicates; track tool) {
                        <mat-chip class="warning-chip">{{ tool }}</mat-chip>
                      }
                    </div>
                  </div>
                }
                
                @if (importResult()!.errors.length > 0) {
                  <div class="result-section">
                    <h4>Errors</h4>
                    <ul class="error-list">
                      @for (error of importResult()!.errors; track error) {
                        <li>{{ error }}</li>
                      }
                    </ul>
                  </div>
                }
              </div>
            }
            
            <div class="step-actions">
              <button mat-raised-button color="primary" (click)="close()">
                Done
              </button>
            </div>
          </div>
        </mat-step>
      </mat-stepper>
    </mat-dialog-content>
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
    }
    
    mat-dialog-content {
      width: 900px;
      max-width: 95vw;
      min-height: 500px;
      padding: 20px 24px;
    }
    
    .step-content {
      padding: 20px 0;
    }
    
    .full-width {
      width: 100%;
    }
    
    .half-width {
      width: calc(50% - 10px);
      margin-right: 20px;
    }
    
    .step-actions {
      display: flex;
      gap: 10px;
      margin-top: 20px;
      justify-content: flex-end;
      align-items: center;
      
      button {
        border-radius: 4px;
      }
      
      button[mat-raised-button]:not([color]) {
        background-color: #ff5722; /* Orangish-red */
        color: white;
      }
      
      .action-button {
        min-width: 160px;
        
        /* Target the internal label wrapper for proper alignment in MDC buttons */
        ::ng-deep .mdc-button__label {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          width: 100%;
        }
        
        mat-icon {
          font-size: 20px;
          height: 20px;
          width: 20px;
          margin: 0;
          line-height: 1;
        }
        
        .button-spinner {
          margin: 0;
        }
        
        ::ng-deep .mat-mdc-progress-spinner circle {
          stroke: currentColor;
        }
      }
    }
    
    .api-info {
      margin-bottom: 20px;
      padding: 15px;
      background: #f5f5f5;
      border-radius: 8px;
      
      h3 {
        margin: 0 0 10px 0;
        
        .version {
          font-size: 0.8em;
          color: #666;
        }
      }
      
      .description {
        color: #666;
        margin: 0 0 10px 0;
      }
      
      .meta {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }
    }
    
    .selection-controls {
      display: flex;
      gap: 10px;
      margin-bottom: 15px;
      align-items: center;
      
      .selection-count {
        margin-left: auto;
        color: #666;
      }
    }
    
    .endpoints-table-container {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
    }
    
    .endpoints-table {
      width: 100%;
      
      code {
        font-family: monospace;
        font-size: 0.85em;
        background: #f0f0f0;
        padding: 2px 6px;
        border-radius: 3px;
        
        &.duplicate {
          background: #fff3cd;
          color: #856404;
        }
      }
    }
    
    .duplicate-row {
      opacity: 0.6;
      background: #fff8e1;
    }
    
    .duplicate-icon {
      font-size: 16px;
      height: 16px;
      width: 16px;
      vertical-align: middle;
      margin-left: 5px;
      color: #ff9800;
    }
    
    .method-get { background: #61affe !important; color: white !important; }
    .method-post { background: #49cc90 !important; color: white !important; }
    .method-put { background: #fca130 !important; color: white !important; }
    .method-delete { background: #f93e3e !important; color: white !important; }
    .method-patch { background: #50e3c2 !important; color: white !important; }
    
    .import-options {
      margin-top: 20px;
      padding: 15px;
      background: #fafafa;
      border-radius: 8px;
      
      h4 {
        margin: 0 0 15px 0;
      }
    }
    
    .checkbox-options {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 10px;
    }
    
    .error-message {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      background: #ffebee;
      color: #c62828;
      border-radius: 4px;
      margin: 10px 0;
    }
    
    .success-message {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px;
      background: #e8f5e9;
      color: #2e7d32;
      border-radius: 4px;
      margin: 10px 0;
    }
    
    .warning {
      background: #fff3cd !important;
      color: #856404 !important;
    }
    
    .results {
      .result-section {
        margin: 20px 0;
        
        h4 {
          margin: 0 0 10px 0;
        }
      }
      
      .tool-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      
      .success-chip {
        background: #e8f5e9 !important;
        color: #2e7d32 !important;
      }
      
      .warning-chip {
        background: #fff3cd !important;
        color: #856404 !important;
      }
      
      .error-list {
        margin: 0;
        padding-left: 20px;
        color: #c62828;
      }
    }
  `]
})
export class SwaggerImportDialogComponent {
  private dialogRef = inject(MatDialogRef<SwaggerImportDialogComponent>);
  private apiService = inject(ApiService);
  
  @ViewChild('stepper') stepper!: MatStepper;
  
  swaggerUrl = '';
  preview = signal<SwaggerPreviewResponse | null>(null);
  previewLoaded = signal(false);
  previewError = signal<string | null>(null);
  loading = signal(false);
  
  selectedEndpoints: Record<string, boolean> = {};
  displayedColumns = ['select', 'method', 'path', 'summary', 'tool_id'];
  
  importOptions = {
    auth_type: 'none',
    auth_env_var: '',
    forward_user_context: true,  // Default to true for Keycloak auth with x-client headers
    timeout: 30,
    enabled: true
  };
  
  importing = signal(false);
  importError = signal<string | null>(null);
  importResult = signal<SwaggerImportResult | null>(null);
  
  async loadPreview(): Promise<void> {
    if (!this.swaggerUrl) return;
    
    this.loading.set(true);
    this.previewError.set(null);
    
    this.apiService.previewSwaggerImport(this.swaggerUrl).subscribe({
      next: (response) => {
        this.preview.set(response);
        this.previewLoaded.set(true);
        this.loading.set(false);
        
        // Auto-select non-duplicate endpoints
        this.selectNonDuplicates();
        
        // Move to next step
        setTimeout(() => this.stepper.next(), 100);
      },
      error: (err) => {
        this.previewError.set(err.error?.detail || 'Failed to load Swagger specification');
        this.loading.set(false);
      }
    });
  }
  
  selectAll(): void {
    const preview = this.preview();
    if (!preview) return;
    
    for (const endpoint of preview.endpoints) {
      if (!endpoint.is_duplicate) {
        this.selectedEndpoints[endpoint.operation_id] = true;
      }
    }
  }
  
  deselectAll(): void {
    this.selectedEndpoints = {};
  }
  
  selectNonDuplicates(): void {
    this.deselectAll();
    this.selectAll();
  }
  
  selectedCount(): number {
    return Object.values(this.selectedEndpoints).filter(v => v).length;
  }
  
  async importTools(): Promise<void> {
    const preview = this.preview();
    if (!preview) return;
    
    const selectedIds = Object.entries(this.selectedEndpoints)
      .filter(([_, selected]) => selected)
      .map(([id, _]) => id);
    
    if (selectedIds.length === 0) return;
    
    this.importing.set(true);
    this.importError.set(null);
    
    this.apiService.importSwaggerTools({
      swagger_url: this.swaggerUrl,
      endpoint_filter: selectedIds,
      auth_type: this.importOptions.auth_type,
      auth_env_var: this.importOptions.auth_type !== 'none' ? this.importOptions.auth_env_var : undefined,
      forward_user_context: this.importOptions.forward_user_context,
      timeout: this.importOptions.timeout,
      enabled: this.importOptions.enabled
    }).subscribe({
      next: (result) => {
        this.importResult.set(result);
        this.importing.set(false);
      },
      error: (err) => {
        this.importError.set(err.error?.detail || 'Failed to import tools');
        this.importing.set(false);
      }
    });
  }
  
  close(): void {
    this.dialogRef.close(this.importResult()?.success ? 'imported' : null);
  }
}
