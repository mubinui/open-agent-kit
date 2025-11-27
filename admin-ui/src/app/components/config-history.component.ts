import { Component, Inject, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef, MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Observable } from 'rxjs';
import { ApiService, ConfigHistoryEntry } from '../services/api.service';
import { DiffViewerComponent } from './diff-viewer.component';
import { ConfirmDialogComponent } from './confirm-dialog.component';

export interface ConfigHistoryData {
  configType: 'agent' | 'tool' | 'workflow';
  configId: string;
  configName: string;
}

@Component({
  selector: 'app-config-history',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>history</mat-icon>
      Change History: {{ data.configName }}
    </h2>
    
    <mat-dialog-content>
      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else {
        <div class="history-container">
          <table mat-table [dataSource]="history()" class="history-table">
            <!-- Version Column -->
            <ng-container matColumnDef="version">
              <th mat-header-cell *matHeaderCellDef>Version</th>
              <td mat-cell *matCellDef="let entry">
                <span class="version-badge">v{{ entry.version }}</span>
              </td>
            </ng-container>

            <!-- Timestamp Column -->
            <ng-container matColumnDef="timestamp">
              <th mat-header-cell *matHeaderCellDef>Date & Time</th>
              <td mat-cell *matCellDef="let entry">
                {{ formatTimestamp(entry.timestamp) }}
              </td>
            </ng-container>

            <!-- Updated By Column -->
            <ng-container matColumnDef="updated_by">
              <th mat-header-cell *matHeaderCellDef>Updated By</th>
              <td mat-cell *matCellDef="let entry">
                {{ entry.updated_by || 'Unknown' }}
              </td>
            </ng-container>

            <!-- Summary Column -->
            <ng-container matColumnDef="summary">
              <th mat-header-cell *matHeaderCellDef>Summary</th>
              <td mat-cell *matCellDef="let entry">
                {{ entry.summary || 'Configuration updated' }}
              </td>
            </ng-container>

            <!-- Actions Column -->
            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef>Actions</th>
              <td mat-cell *matCellDef="let entry">
                <button 
                  mat-icon-button 
                  color="primary" 
                  (click)="viewConfig(entry)"
                  matTooltip="View Configuration">
                  <mat-icon>visibility</mat-icon>
                </button>
                <button 
                  mat-icon-button 
                  color="accent" 
                  (click)="compareWithCurrent(entry)"
                  matTooltip="Compare with Current">
                  <mat-icon>compare_arrows</mat-icon>
                </button>
                <button 
                  mat-icon-button 
                  color="warn" 
                  (click)="rollbackToVersion(entry)"
                  matTooltip="Rollback to this Version"
                  [disabled]="entry.version === currentVersion()">
                  <mat-icon>restore</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>

          @if (history().length === 0) {
            <div class="empty-state">
              <p>No history available for this configuration.</p>
            </div>
          }
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="onClose()">
        Close
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    h2 {
      display: flex;
      align-items: center;
      gap: 8px;

      mat-icon {
        font-size: 24px;
        width: 24px;
        height: 24px;
      }
    }

    mat-dialog-content {
      min-height: 400px;
      max-height: 600px;
      overflow-y: auto;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 400px;
    }

    .history-container {
      padding: 16px 0;
    }

    .history-table {
      width: 100%;

      th {
        font-weight: 600;
        color: #666;
      }

      td {
        padding: 12px 8px;
      }

      button {
        margin: 0 2px;
      }
    }

    .version-badge {
      display: inline-block;
      padding: 4px 8px;
      background-color: #e3f2fd;
      color: #1976d2;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }

    .empty-state {
      text-align: center;
      padding: 48px 24px;
      color: #666;

      p {
        font-size: 14px;
      }
    }

    mat-dialog-actions {
      padding: 16px 24px;
    }
  `]
})
export class ConfigHistoryComponent {
  private apiService = inject(ApiService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  history = signal<ConfigHistoryEntry[]>([]);
  loading = signal(true);
  currentVersion = signal(1);
  displayedColumns = ['version', 'timestamp', 'updated_by', 'summary', 'actions'];

  constructor(
    public dialogRef: MatDialogRef<ConfigHistoryComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfigHistoryData
  ) {
    this.loadHistory();
  }

  loadHistory(): void {
    this.loading.set(true);
    
    let historyObservable;
    switch (this.data.configType) {
      case 'agent':
        historyObservable = this.apiService.getAgentHistory(this.data.configId);
        break;
      case 'tool':
        historyObservable = this.apiService.getToolHistory(this.data.configId);
        break;
      case 'workflow':
        historyObservable = this.apiService.getWorkflowHistory(this.data.configId);
        break;
    }

    historyObservable.subscribe({
      next: (data) => {
        this.history.set(data);
        if (data.length > 0) {
          this.currentVersion.set(data[0].version);
        }
        this.loading.set(false);
      },
      error: (err) => {
        this.snackBar.open('Failed to load history', 'Close', { duration: 3000 });
        this.loading.set(false);
        console.error('Error loading history:', err);
      }
    });
  }

  formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleString();
  }

  viewConfig(entry: ConfigHistoryEntry): void {
    this.dialog.open(DiffViewerComponent, {
      width: '800px',
      height: '600px',
      data: {
        leftContent: JSON.stringify(entry.config, null, 2),
        rightContent: '',
        leftLabel: `Version ${entry.version} - ${this.formatTimestamp(entry.timestamp)}`,
        rightLabel: ''
      }
    });
  }

  compareWithCurrent(entry: ConfigHistoryEntry): void {
    const currentEntry = this.history()[0];
    this.dialog.open(DiffViewerComponent, {
      width: '90vw',
      height: '80vh',
      data: {
        leftContent: JSON.stringify(entry.config, null, 2),
        rightContent: JSON.stringify(currentEntry.config, null, 2),
        leftLabel: `Version ${entry.version} - ${this.formatTimestamp(entry.timestamp)}`,
        rightLabel: `Current Version ${currentEntry.version} - ${this.formatTimestamp(currentEntry.timestamp)}`
      }
    });
  }

  rollbackToVersion(entry: ConfigHistoryEntry): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: 'Rollback Configuration',
        message: `Are you sure you want to rollback to version ${entry.version}? This will create a new version with the configuration from v${entry.version}.`
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.performRollback(entry.version);
      }
    });
  }

  performRollback(targetVersion: number): void {
    let rollbackObservable: Observable<any>;
    switch (this.data.configType) {
      case 'agent':
        rollbackObservable = this.apiService.rollbackAgent(this.data.configId, targetVersion);
        break;
      case 'tool':
        rollbackObservable = this.apiService.rollbackTool(this.data.configId, targetVersion);
        break;
      case 'workflow':
        rollbackObservable = this.apiService.rollbackWorkflow(this.data.configId, targetVersion);
        break;
      default:
        return;
    }

    rollbackObservable.subscribe({
      next: () => {
        this.snackBar.open(`Rolled back to version ${targetVersion}`, 'Close', { duration: 3000 });
        this.dialogRef.close({ action: 'rollback', version: targetVersion });
      },
      error: (err: any) => {
        this.snackBar.open('Failed to rollback configuration', 'Close', { duration: 3000 });
        console.error('Error rolling back:', err);
      }
    });
  }

  onClose(): void {
    this.dialogRef.close();
  }
}
