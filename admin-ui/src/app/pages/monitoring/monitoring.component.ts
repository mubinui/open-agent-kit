import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { ApiService, DashboardMetrics } from '../../services/api.service';

interface ErrorLog {
  timestamp: string;
  level: string;
  message: string;
  details?: string;
}

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatChipsModule
  ],
  templateUrl: './monitoring.component.html',
  styleUrl: './monitoring.component.scss'
})
export class MonitoringComponent implements OnInit {
  private apiService = inject(ApiService);

  metrics = signal<DashboardMetrics | null>(null);
  errorLogs = signal<ErrorLog[]>([]);
  loading = signal(true);
  autoRefresh = signal(true);
  displayedColumns = ['timestamp', 'level', 'message'];

  ngOnInit(): void {
    this.loadData();
    this.startAutoRefresh();
  }

  loadData(): void {
    this.loading.set(true);
    this.apiService.getMetrics().subscribe({
      next: (data) => {
        this.metrics.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Error loading metrics:', err);
        this.loading.set(false);
      }
    });

    // Mock error logs - in production, this would come from an API endpoint
    this.errorLogs.set([
      {
        timestamp: new Date().toISOString(),
        level: 'ERROR',
        message: 'Failed to connect to LLM provider',
        details: 'Connection timeout after 30 seconds'
      },
      {
        timestamp: new Date(Date.now() - 300000).toISOString(),
        level: 'WARNING',
        message: 'High memory usage detected',
        details: 'Memory usage at 85%'
      },
      {
        timestamp: new Date(Date.now() - 600000).toISOString(),
        level: 'ERROR',
        message: 'Agent execution failed',
        details: 'Agent "assistant" exceeded max retries'
      }
    ]);
  }

  startAutoRefresh(): void {
    setInterval(() => {
      if (this.autoRefresh()) {
        this.loadData();
      }
    }, 10000); // Refresh every 10 seconds
  }

  toggleAutoRefresh(): void {
    this.autoRefresh.update(v => !v);
  }

  refreshData(): void {
    this.loadData();
  }

  clearLogs(): void {
    this.errorLogs.set([]);
  }
}
