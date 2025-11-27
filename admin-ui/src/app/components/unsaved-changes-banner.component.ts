import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-unsaved-changes-banner',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    @if (hasUnsavedChanges || hasVersionConflict) {
      <div class="warning-banner" [class.conflict]="hasVersionConflict">
        <div class="banner-content">
          <mat-icon>{{ hasVersionConflict ? 'warning' : 'info' }}</mat-icon>
          <div class="message">
            @if (hasVersionConflict) {
              <strong>Version Conflict:</strong> This configuration has been updated by another user.
              Your local version (v{{ localVersion }}) differs from the server version (v{{ serverVersion }}).
            } @else if (hasUnsavedChanges) {
              <strong>Unsaved Changes:</strong> You have unsaved changes to this configuration.
            }
          </div>
        </div>
        <div class="banner-actions">
          @if (hasVersionConflict) {
            <button mat-button (click)="onCheckForUpdates()">
              <mat-icon>refresh</mat-icon>
              Check for Updates
            </button>
          }
          @if (autoRefreshEnabled) {
            <button mat-button (click)="onToggleAutoRefresh()">
              <mat-icon>pause</mat-icon>
              Disable Auto-Refresh
            </button>
          } @else {
            <button mat-button (click)="onToggleAutoRefresh()">
              <mat-icon>play_arrow</mat-icon>
              Enable Auto-Refresh
            </button>
          }
          <button mat-icon-button (click)="onDismiss()">
            <mat-icon>close</mat-icon>
          </button>
        </div>
      </div>
    }
  `,
  styles: [`
    .warning-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      margin-bottom: 16px;
      background-color: #fff3e0;
      border-left: 4px solid #ff9800;
      border-radius: 4px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

      &.conflict {
        background-color: #ffebee;
        border-left-color: #f44336;

        mat-icon {
          color: #f44336;
        }
      }
    }

    .banner-content {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;

      mat-icon {
        color: #ff9800;
        font-size: 24px;
        width: 24px;
        height: 24px;
      }

      .message {
        font-size: 14px;
        color: #333;

        strong {
          font-weight: 600;
        }
      }
    }

    .banner-actions {
      display: flex;
      align-items: center;
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
export class UnsavedChangesBannerComponent {
  @Input() hasUnsavedChanges = false;
  @Input() hasVersionConflict = false;
  @Input() localVersion = 1;
  @Input() serverVersion = 1;
  @Input() autoRefreshEnabled = false;

  @Output() checkForUpdates = new EventEmitter<void>();
  @Output() toggleAutoRefresh = new EventEmitter<void>();
  @Output() dismiss = new EventEmitter<void>();

  onCheckForUpdates(): void {
    this.checkForUpdates.emit();
  }

  onToggleAutoRefresh(): void {
    this.toggleAutoRefresh.emit();
  }

  onDismiss(): void {
    this.dismiss.emit();
  }
}
