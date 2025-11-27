import { Component, OnInit, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
import { AgentConfig } from '../../models/agent.model';
import { AgentFormDialogComponent } from './agent-form-dialog.component';
import { ConfirmDialogComponent } from '../../components/confirm-dialog.component';
import { ConflictDialogComponent } from '../../components/conflict-dialog.component';
import { ConfigHistoryComponent } from '../../components/config-history.component';
import { ConfigVersionService } from '../../services/config-version.service';

@Component({
  selector: 'app-agents',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './agents.component.html',
  styleUrl: './agents.component.scss'
})
export class AgentsComponent implements OnInit, OnDestroy {
  private apiService = inject(ApiService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private versionService = inject(ConfigVersionService);

  agents = signal<AgentConfig[]>([]);
  loading = signal(true);
  displayedColumns = ['id', 'name', 'type', 'version', 'last_updated', 'tools', 'actions'];

  ngOnInit(): void {
    this.loadAgents();
  }

  ngOnDestroy(): void {
    this.versionService.disableAutoRefresh();
  }

  loadAgents(): void {
    this.loading.set(true);
    this.apiService.getAgents().subscribe({
      next: (data) => {
        this.agents.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.snackBar.open('Failed to load agents', 'Close', { duration: 3000 });
        this.loading.set(false);
        console.error('Error loading agents:', err);
      }
    });
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(AgentFormDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { agent: null }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.createAgent(result);
      }
    });
  }

  openEditDialog(agent: AgentConfig): void {
    const dialogRef = this.dialog.open(AgentFormDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { agent: { ...agent } }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.updateAgent(agent.id, result);
      }
    });
  }

  createAgent(agent: AgentConfig): void {
    this.apiService.createAgent(agent).subscribe({
      next: () => {
        this.snackBar.open('Agent created successfully', 'Close', { duration: 3000 });
        this.loadAgents();
      },
      error: (err) => {
        this.snackBar.open('Failed to create agent', 'Close', { duration: 3000 });
        console.error('Error creating agent:', err);
      }
    });
  }

  updateAgent(agentId: string, agent: AgentConfig): void {
    const versionToken = agent.etag;
    
    this.apiService.updateAgent(agentId, agent, versionToken).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 409) {
          // Conflict detected
          this.handleConflict(agentId, agent, error.error);
          return throwError(() => error);
        }
        return throwError(() => error);
      })
    ).subscribe({
      next: () => {
        this.snackBar.open('Agent updated successfully', 'Close', { duration: 3000 });
        this.loadAgents();
      },
      error: (err) => {
        if (err.status !== 409) {
          this.snackBar.open('Failed to update agent', 'Close', { duration: 3000 });
          console.error('Error updating agent:', err);
        }
      }
    });
  }

  handleConflict(agentId: string, yourChanges: AgentConfig, conflictData: any): void {
    const dialogRef = this.dialog.open(ConflictDialogComponent, {
      width: '800px',
      disableClose: true,
      data: {
        configType: 'agent',
        configId: agentId,
        currentVersion: conflictData.current_version,
        yourVersion: yourChanges.version || 1,
        currentConfig: conflictData.current_config,
        yourChanges: yourChanges,
        diff: conflictData.diff
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.action === 'reload') {
        this.loadAgents();
      }
    });
  }

  openHistoryDialog(agent: AgentConfig): void {
    const dialogRef = this.dialog.open(ConfigHistoryComponent, {
      width: '900px',
      height: '700px',
      data: {
        configType: 'agent',
        configId: agent.id,
        configName: agent.name
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.action === 'rollback') {
        this.loadAgents();
      }
    });
  }

  openDeleteDialog(agent: AgentConfig): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: 'Delete Agent',
        message: `Are you sure you want to delete agent "${agent.name}"?`
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.deleteAgent(agent.id);
      }
    });
  }

  deleteAgent(agentId: string): void {
    this.apiService.deleteAgent(agentId).subscribe({
      next: () => {
        this.snackBar.open('Agent deleted successfully', 'Close', { duration: 3000 });
        this.loadAgents();
      },
      error: (err) => {
        this.snackBar.open('Failed to delete agent', 'Close', { duration: 3000 });
        console.error('Error deleting agent:', err);
      }
    });
  }

  testAgent(agent: AgentConfig): void {
    this.snackBar.open(`Testing agent: ${agent.name}`, 'Close', { duration: 2000 });
    // TODO: Implement agent testing functionality
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
