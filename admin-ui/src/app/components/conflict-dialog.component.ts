import { Component, Inject, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef, MatDialog } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { DiffViewerComponent } from './diff-viewer.component';

export interface ConflictDialogData {
  configType: string;
  configId: string;
  currentVersion: number;
  yourVersion: number;
  currentConfig: any;
  yourChanges: any;
  diff: {
    added: string[];
    removed: string[];
    modified: Array<{ field: string; current: any; yours: any }>;
  };
}

@Component({
  selector: 'app-conflict-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatCardModule
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon color="warn">warning</mat-icon>
      Configuration Conflict Detected
    </h2>
    
    <mat-dialog-content>
      <div class="conflict-info">
        <p class="conflict-message">
          The {{ data.configType }} configuration has been modified by another user.
          Your version (v{{ data.yourVersion }}) conflicts with the current version (v{{ data.currentVersion }}).
        </p>
      </div>

      <mat-tab-group>
        <mat-tab label="Summary">
          <div class="tab-content">
            <div class="diff-summary">
              @if (data.diff.added.length > 0) {
                <mat-card class="diff-card added">
                  <mat-card-header>
                    <mat-icon>add_circle</mat-icon>
                    <span>Added Fields ({{ data.diff.added.length }})</span>
                  </mat-card-header>
                  <mat-card-content>
                    <ul>
                      @for (field of data.diff.added; track field) {
                        <li>{{ field }}</li>
                      }
                    </ul>
                  </mat-card-content>
                </mat-card>
              }

              @if (data.diff.removed.length > 0) {
                <mat-card class="diff-card removed">
                  <mat-card-header>
                    <mat-icon>remove_circle</mat-icon>
                    <span>Removed Fields ({{ data.diff.removed.length }})</span>
                  </mat-card-header>
                  <mat-card-content>
                    <ul>
                      @for (field of data.diff.removed; track field) {
                        <li>{{ field }}</li>
                      }
                    </ul>
                  </mat-card-content>
                </mat-card>
              }

              @if (data.diff.modified.length > 0) {
                <mat-card class="diff-card modified">
                  <mat-card-header>
                    <mat-icon>edit</mat-icon>
                    <span>Modified Fields ({{ data.diff.modified.length }})</span>
                  </mat-card-header>
                  <mat-card-content>
                    <ul>
                      @for (item of data.diff.modified; track item.field) {
                        <li>
                          <strong>{{ item.field }}</strong>
                          <div class="value-comparison">
                            <div class="current-value">
                              <span class="label">Current:</span>
                              <code>{{ formatValue(item.current) }}</code>
                            </div>
                            <div class="your-value">
                              <span class="label">Yours:</span>
                              <code>{{ formatValue(item.yours) }}</code>
                            </div>
                          </div>
                        </li>
                      }
                    </ul>
                  </mat-card-content>
                </mat-card>
              }
            </div>
          </div>
        </mat-tab>

        <mat-tab label="Current Version">
          <div class="tab-content">
            <pre class="config-preview">{{ formatJSON(data.currentConfig) }}</pre>
          </div>
        </mat-tab>

        <mat-tab label="Your Changes">
          <div class="tab-content">
            <pre class="config-preview">{{ formatJSON(data.yourChanges) }}</pre>
          </div>
        </mat-tab>
      </mat-tab-group>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="downloadYourChanges()">
        <mat-icon>download</mat-icon>
        Download Your Changes
      </button>
      <button mat-button (click)="viewSideBySide()">
        <mat-icon>compare_arrows</mat-icon>
        View Side-by-Side
      </button>
      <button mat-button (click)="onCancel()">
        Cancel
      </button>
      <button mat-raised-button color="primary" (click)="reloadLatest()">
        <mat-icon>refresh</mat-icon>
        Reload Latest
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
      display: block;
    }

    mat-dialog-content {
      width: 700px;
      max-width: 95vw;
      max-height: 70vh;
      padding: 0 24px;
      box-sizing: border-box;
      overflow-y: auto;
      overflow-x: hidden;
    }

    .conflict-info {
      margin-bottom: 20px;
      padding: 16px;
      background-color: #fff3e0;
      border-left: 4px solid #ff9800;
      border-radius: 4px;
    }

    .conflict-message {
      margin: 0;
      color: #e65100;
      font-size: 14px;
      line-height: 1.5;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #d32f2f;
      margin: 0;
      padding: 16px 24px;

      mat-icon {
        font-size: 28px;
        width: 28px;
        height: 28px;
      }
    }

    .tab-content {
      padding: 16px;
      min-height: 250px;
      max-height: 400px;
      overflow-y: auto;
    }

    .diff-summary {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .diff-card {
      mat-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        font-weight: 600;
      }

      &.added {
        border-left: 4px solid #4caf50;
        
        mat-icon {
          color: #4caf50;
        }
      }

      &.removed {
        border-left: 4px solid #f44336;
        
        mat-icon {
          color: #f44336;
        }
      }

      &.modified {
        border-left: 4px solid #ff9800;
        
        mat-icon {
          color: #ff9800;
        }
      }

      ul {
        margin: 0;
        padding-left: 20px;
      }

      li {
        margin-bottom: 8px;
      }
    }

    .value-comparison {
      margin-top: 8px;
      padding-left: 16px;
      font-size: 13px;

      .label {
        font-weight: 600;
        margin-right: 8px;
      }

      code {
        background-color: #f5f5f5;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 12px;
      }

      .current-value {
        margin-bottom: 4px;
      }
    }

    .config-preview {
      background-color: #f5f5f5;
      padding: 16px;
      border-radius: 4px;
      overflow-x: auto;
      font-size: 13px;
      line-height: 1.5;
    }

    mat-dialog-actions {
      padding: 16px 24px;
      gap: 8px;

      button {
        mat-icon {
          margin-right: 4px;
          font-size: 18px;
          width: 18px;
          height: 18px;
        }
      }
    }
  `]
})
export class ConflictDialogComponent {
  private dialog = inject(MatDialog);

  constructor(
    public dialogRef: MatDialogRef<ConflictDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConflictDialogData
  ) {}

  formatJSON(obj: any): string {
    return JSON.stringify(obj, null, 2);
  }

  formatValue(value: any): string {
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }

  downloadYourChanges(): void {
    const dataStr = JSON.stringify(this.data.yourChanges, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${this.data.configType}-${this.data.configId}-v${this.data.yourVersion}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  viewSideBySide(): void {
    this.dialog.open(DiffViewerComponent, {
      width: '90vw',
      height: '80vh',
      data: {
        leftContent: this.formatJSON(this.data.currentConfig),
        rightContent: this.formatJSON(this.data.yourChanges),
        leftLabel: `Current Version (v${this.data.currentVersion})`,
        rightLabel: `Your Changes (v${this.data.yourVersion})`
      }
    });
  }

  reloadLatest(): void {
    this.dialogRef.close({ action: 'reload' });
  }

  onCancel(): void {
    this.dialogRef.close({ action: 'cancel' });
  }
}
