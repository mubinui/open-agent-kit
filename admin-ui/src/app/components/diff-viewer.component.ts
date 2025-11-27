import { Component, Inject, OnInit, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface DiffViewerData {
  leftContent: string;
  rightContent: string;
  leftLabel: string;
  rightLabel: string;
}

@Component({
  selector: 'app-diff-viewer',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>compare_arrows</mat-icon>
      Configuration Comparison
    </h2>
    
    <mat-dialog-content>
      <div class="diff-container">
        <div class="diff-header">
          <div class="left-header">{{ data.leftLabel }}</div>
          <div class="right-header">{{ data.rightLabel }}</div>
        </div>
        <div class="diff-content" #diffContent>
          <div class="side-by-side">
            <div class="left-side">
              <pre>{{ data.leftContent }}</pre>
            </div>
            <div class="right-side">
              <pre>{{ data.rightContent }}</pre>
            </div>
          </div>
        </div>
      </div>
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
      padding: 0;
      margin: 0;
      overflow: hidden;
    }

    .diff-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .diff-header {
      display: grid;
      grid-template-columns: 1fr 1fr;
      background-color: #f5f5f5;
      border-bottom: 2px solid #ddd;
      font-weight: 600;
      font-size: 14px;

      .left-header,
      .right-header {
        padding: 12px 16px;
        text-align: center;
      }

      .left-header {
        border-right: 1px solid #ddd;
        background-color: #ffebee;
      }

      .right-header {
        background-color: #e8f5e9;
      }
    }

    .diff-content {
      flex: 1;
      overflow: auto;
      max-height: calc(80vh - 200px);
    }

    .side-by-side {
      display: grid;
      grid-template-columns: 1fr 1fr;
      min-height: 100%;
    }

    .left-side,
    .right-side {
      overflow-x: auto;
      border-right: 1px solid #ddd;

      pre {
        margin: 0;
        padding: 16px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre;
        background-color: #fafafa;
      }
    }

    .left-side {
      background-color: #fff5f5;
    }

    .right-side {
      background-color: #f5fff5;
      border-right: none;
    }

    mat-dialog-actions {
      padding: 16px 24px;
    }
  `]
})
export class DiffViewerComponent implements OnInit, AfterViewInit {
  @ViewChild('diffContent') diffContent!: ElementRef;

  constructor(
    public dialogRef: MatDialogRef<DiffViewerComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DiffViewerData
  ) {}

  ngOnInit(): void {
    // Component initialization
  }

  ngAfterViewInit(): void {
    // Sync scroll between left and right sides
    const leftSide = this.diffContent.nativeElement.querySelector('.left-side');
    const rightSide = this.diffContent.nativeElement.querySelector('.right-side');

    if (leftSide && rightSide) {
      leftSide.addEventListener('scroll', () => {
        rightSide.scrollTop = leftSide.scrollTop;
      });

      rightSide.addEventListener('scroll', () => {
        leftSide.scrollTop = rightSide.scrollTop;
      });
    }
  }

  onClose(): void {
    this.dialogRef.close();
  }
}
