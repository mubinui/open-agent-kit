import { Component, OnInit, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { ToolConfig } from '../../models/tool.model';
import { ToolFormDialogComponent } from './tool-form-dialog.component';
import { ToolTestDialogComponent } from './tool-test-dialog.component';
import { ConfirmDialogComponent } from '../../components/confirm-dialog.component';
import { ConflictDialogComponent } from '../../components/conflict-dialog.component';
import { ConfigHistoryComponent } from '../../components/config-history.component';
import { ConfigVersionService } from '../../services/config-version.service';

@Component({
  selector: 'app-tools',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule
  ],
  templateUrl: './tools.component.html',
  styleUrl: './tools.component.scss'
})
export class ToolsComponent implements OnInit, OnDestroy {
  private apiService = inject(ApiService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private versionService = inject(ConfigVersionService);

  tools = signal<ToolConfig[]>([]);
  loading = signal(true);
  displayedColumns = ['id', 'name', 'description', 'version', 'last_updated', 'enabled', 'actions'];

  ngOnInit(): void {
    this.loadTools();
  }

  ngOnDestroy(): void {
    this.versionService.disableAutoRefresh();
  }

  loadTools(): void {
    this.loading.set(true);
    this.apiService.getTools().subscribe({
      next: (data) => {
        this.tools.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.snackBar.open('Failed to load tools', 'Close', { duration: 3000 });
        this.loading.set(false);
        console.error('Error loading tools:', err);
      }
    });
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(ToolFormDialogComponent, {
      width: '850px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { tool: null }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.createTool(result);
      }
    });
  }

  openEditDialog(tool: ToolConfig): void {
    const dialogRef = this.dialog.open(ToolFormDialogComponent, {
      width: '850px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { tool: { ...tool } }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.updateTool(tool.id, result);
      }
    });
  }

  createTool(tool: ToolConfig): void {
    this.apiService.createTool(tool).subscribe({
      next: () => {
        this.snackBar.open('Tool registered successfully', 'Close', { duration: 3000 });
        this.loadTools();
      },
      error: (err) => {
        this.snackBar.open('Failed to register tool', 'Close', { duration: 3000 });
        console.error('Error creating tool:', err);
      }
    });
  }

  updateTool(toolId: string, tool: ToolConfig): void {
    const versionToken = tool.etag;
    
    this.apiService.updateTool(toolId, tool, versionToken).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 409) {
          this.handleConflict(toolId, tool, error.error);
          return throwError(() => error);
        }
        return throwError(() => error);
      })
    ).subscribe({
      next: () => {
        this.snackBar.open('Tool updated successfully', 'Close', { duration: 3000 });
        this.loadTools();
      },
      error: (err) => {
        if (err.status !== 409) {
          this.snackBar.open('Failed to update tool', 'Close', { duration: 3000 });
          console.error('Error updating tool:', err);
        }
      }
    });
  }

  handleConflict(toolId: string, yourChanges: ToolConfig, conflictData: any): void {
    const dialogRef = this.dialog.open(ConflictDialogComponent, {
      width: '800px',
      disableClose: true,
      data: {
        configType: 'tool',
        configId: toolId,
        currentVersion: conflictData.current_version,
        yourVersion: yourChanges.version || 1,
        currentConfig: conflictData.current_config,
        yourChanges: yourChanges,
        diff: conflictData.diff
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.action === 'reload') {
        this.loadTools();
      }
    });
  }

  openHistoryDialog(tool: ToolConfig): void {
    const dialogRef = this.dialog.open(ConfigHistoryComponent, {
      width: '900px',
      height: '700px',
      data: {
        configType: 'tool',
        configId: tool.id,
        configName: tool.name
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.action === 'rollback') {
        this.loadTools();
      }
    });
  }

  openDeleteDialog(tool: ToolConfig): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: 'Delete Tool',
        message: `Are you sure you want to delete tool "${tool.name}"?`
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.deleteTool(tool.id);
      }
    });
  }

  deleteTool(toolId: string): void {
    this.apiService.deleteTool(toolId).subscribe({
      next: () => {
        this.snackBar.open('Tool deleted successfully', 'Close', { duration: 3000 });
        this.loadTools();
      },
      error: (err) => {
        this.snackBar.open('Failed to delete tool', 'Close', { duration: 3000 });
        console.error('Error deleting tool:', err);
      }
    });
  }

  testTool(tool: ToolConfig): void {
    this.dialog.open(ToolTestDialogComponent, {
      width: '800px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { tool }
    });
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}
