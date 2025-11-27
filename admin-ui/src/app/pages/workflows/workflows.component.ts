import { Component, OnInit, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { WorkflowConfig } from '../../models/workflow.model';
import { WorkflowFormDialogComponent } from './workflow-form-dialog.component';
import { WorkflowVisualizerDialogComponent } from './workflow-visualizer-dialog.component';
import { ConfirmDialogComponent } from '../../components/confirm-dialog.component';
import { ConflictDialogComponent } from '../../components/conflict-dialog.component';
import { ConfigHistoryComponent } from '../../components/config-history.component';
import { ConfigVersionService } from '../../services/config-version.service';

@Component({
  selector: 'app-workflows',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './workflows.component.html',
  styleUrl: './workflows.component.scss'
})
export class WorkflowsComponent implements OnInit, OnDestroy {
  private apiService = inject(ApiService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private versionService = inject(ConfigVersionService);

  workflows = signal<WorkflowConfig[]>([]);
  loading = signal(true);
  displayedColumns = ['id', 'name', 'pattern', 'version', 'last_updated', 'entry_agent', 'actions'];

  ngOnInit(): void {
    this.loadWorkflows();
  }

  ngOnDestroy(): void {
    this.versionService.disableAutoRefresh();
  }

  loadWorkflows(): void {
    this.loading.set(true);
    this.apiService.getWorkflows().subscribe({
      next: (data) => {
        this.workflows.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.snackBar.open('Failed to load workflows', 'Close', { duration: 3000 });
        this.loading.set(false);
        console.error('Error loading workflows:', err);
      }
    });
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(WorkflowFormDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { workflow: null }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.createWorkflow(result);
      }
    });
  }

  openEditDialog(workflow: WorkflowConfig): void {
    const dialogRef = this.dialog.open(WorkflowFormDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { workflow: { ...workflow } }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.updateWorkflow(workflow.id, result);
      }
    });
  }

  openVisualizerDialog(workflow: WorkflowConfig): void {
    this.dialog.open(WorkflowVisualizerDialogComponent, {
      width: '950px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { workflow }
    });
  }

  createWorkflow(workflow: WorkflowConfig): void {
    this.apiService.createWorkflow(workflow).subscribe({
      next: () => {
        this.snackBar.open('Workflow created successfully', 'Close', { duration: 3000 });
        this.loadWorkflows();
      },
      error: (err) => {
        this.snackBar.open('Failed to create workflow', 'Close', { duration: 3000 });
        console.error('Error creating workflow:', err);
      }
    });
  }

  updateWorkflow(workflowId: string, workflow: WorkflowConfig): void {
    const versionToken = workflow.etag;
    
    this.apiService.updateWorkflow(workflowId, workflow, versionToken).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 409) {
          this.handleConflict(workflowId, workflow, error.error);
          return throwError(() => error);
        }
        return throwError(() => error);
      })
    ).subscribe({
      next: () => {
        this.snackBar.open('Workflow updated successfully', 'Close', { duration: 3000 });
        this.loadWorkflows();
      },
      error: (err) => {
        if (err.status !== 409) {
          this.snackBar.open('Failed to update workflow', 'Close', { duration: 3000 });
          console.error('Error updating workflow:', err);
        }
      }
    });
  }

  handleConflict(workflowId: string, yourChanges: WorkflowConfig, conflictData: any): void {
    const dialogRef = this.dialog.open(ConflictDialogComponent, {
      width: '800px',
      disableClose: true,
      data: {
        configType: 'workflow',
        configId: workflowId,
        currentVersion: conflictData.current_version,
        yourVersion: yourChanges.version || 1,
        currentConfig: conflictData.current_config,
        yourChanges: yourChanges,
        diff: conflictData.diff
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.action === 'reload') {
        this.loadWorkflows();
      }
    });
  }

  openHistoryDialog(workflow: WorkflowConfig): void {
    const dialogRef = this.dialog.open(ConfigHistoryComponent, {
      width: '900px',
      height: '700px',
      data: {
        configType: 'workflow',
        configId: workflow.id,
        configName: workflow.name
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.action === 'rollback') {
        this.loadWorkflows();
      }
    });
  }

  openDeleteDialog(workflow: WorkflowConfig): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: 'Delete Workflow',
        message: `Are you sure you want to delete workflow "${workflow.name}"?`
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.deleteWorkflow(workflow.id);
      }
    });
  }

  deleteWorkflow(workflowId: string): void {
    this.apiService.deleteWorkflow(workflowId).subscribe({
      next: () => {
        this.snackBar.open('Workflow deleted successfully', 'Close', { duration: 3000 });
        this.loadWorkflows();
      },
      error: (err) => {
        this.snackBar.open('Failed to delete workflow', 'Close', { duration: 3000 });
        console.error('Error deleting workflow:', err);
      }
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
