import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../services/api.service';
import { ToolConfig } from '../../models/tool.model';

@Component({
  selector: 'app-tool-test-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  template: `
    <h2 mat-dialog-title>Test Tool: {{ tool.name }}</h2>
    <mat-dialog-content>
      <div class="test-container">
        <div class="input-section">
          <h3>Arguments</h3>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Arguments (JSON)</mat-label>
            <textarea matInput [(ngModel)]="argsJson" rows="5" placeholder='{"arg1": "value1"}'></textarea>
            <mat-hint>Enter arguments as JSON object</mat-hint>
          </mat-form-field>

          <mat-expansion-panel class="context-panel">
            <mat-expansion-panel-header>
              <mat-panel-title>Context Headers</mat-panel-title>
            </mat-expansion-panel-header>

            <div class="context-controls">
              <mat-checkbox [(ngModel)]="enableContext">Enable Context Headers</mat-checkbox>
              
              @if (enableContext) {
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Client Username (x-client-username)</mat-label>
                  <input matInput [(ngModel)]="clientUsername" placeholder="e.g. testuser">
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Client Roles (x-client-ref)</mat-label>
                  <input matInput [(ngModel)]="clientRoles" placeholder="e.g. User, Admin">
                  <mat-hint>Comma separated roles</mat-hint>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Bearer Token (Authorization)</mat-label>
                  <input matInput [(ngModel)]="bearerToken" placeholder="eyJhbGciOi...">
                  <mat-hint>Optional: Override Authorization header</mat-hint>
                </mat-form-field>
              }
            </div>
          </mat-expansion-panel>
        </div>

        <div class="actions">
          <button mat-raised-button color="primary" (click)="execute()" [disabled]="loading || !isValidJson()">
            @if (loading) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              Execute
            }
          </button>
        </div>

        @if (result) {
          <div class="result-section" [class.error]="result.status === 'error'">
            <h3>Result</h3>
            <div class="status-badge" [class.success]="result.status === 'success'" [class.error]="result.status === 'error'">
              {{ result.status | titlecase }}
            </div>
            
            @if (result.error) {
              <div class="error-message">{{ result.error }}</div>
            }
            
            @if (result.result !== undefined) {
              <pre class="result-json">{{ result.result | json }}</pre>
            }
          </div>
        }
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Close</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .test-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding-top: 8px;
    }
    .full-width {
      width: 100%;
    }
    .context-panel {
      margin-top: 8px;
    }
    .context-controls {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-top: 16px;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
    }
    .result-section {
      margin-top: 16px;
      padding: 16px;
      background-color: #f8f9fa;
      border-radius: 4px;
      border: 1px solid #e2e8f0;
      
      &.error {
        background-color: #fff5f5;
        border-color: #feb2b2;
      }
    }
    .status-badge {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      margin-bottom: 8px;
      
      &.success {
        background-color: #d1fae5;
        color: #065f46;
      }
      &.error {
        background-color: #fee2e2;
        color: #991b1b;
      }
    }
    .error-message {
      color: #dc2626;
      margin-bottom: 8px;
    }
    .result-json {
      background-color: #1e293b;
      color: #e2e8f0;
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
      font-family: monospace;
      margin: 0;
    }
  `]
})
export class ToolTestDialogComponent {
  private apiService = inject(ApiService);
  private snackBar = inject(MatSnackBar);
  
  tool: ToolConfig = inject(MAT_DIALOG_DATA).tool;
  
  argsJson = '{}';
  loading = false;
  result: any = null;
  
  // Context
  enableContext = false;
  clientUsername = '';
  clientRoles = '';
  bearerToken = '';

  isValidJson(): boolean {
    try {
      JSON.parse(this.argsJson);
      return true;
    } catch {
      return false;
    }
  }

  execute(): void {
    if (!this.isValidJson()) return;
    
    this.loading = true;
    this.result = null;
    
    const args = JSON.parse(this.argsJson);
    const headers: Record<string, string> = {};
    
    if (this.enableContext) {
      if (this.clientUsername) {
        headers['x-client-username'] = this.clientUsername;
      }
      if (this.clientRoles) {
        const roles = this.clientRoles.split(',').map(r => r.trim()).filter(r => r);
        if (roles.length > 0) {
          headers['x-client-ref'] = JSON.stringify(roles);
        }
      }
      if (this.bearerToken) {
        headers['Authorization'] = `Bearer ${this.bearerToken}`;
      }
    }
    
    this.apiService.executeTool(this.tool.id, args, headers).subscribe({
      next: (res) => {
        this.result = res;
        this.loading = false;
      },
      error: (err) => {
        this.result = {
          status: 'error',
          error: err.message || 'Unknown error occurred'
        };
        this.loading = false;
        this.snackBar.open('Execution failed', 'Close', { duration: 3000 });
      }
    });
  }
}
