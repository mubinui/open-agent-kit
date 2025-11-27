import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { 
    path: 'dashboard', 
    loadComponent: () => import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  { 
    path: 'agents', 
    loadComponent: () => import('./pages/agents/agents.component').then(m => m.AgentsComponent)
  },
  { 
    path: 'tools', 
    loadComponent: () => import('./pages/tools/tools.component').then(m => m.ToolsComponent)
  },
  { 
    path: 'workflows', 
    loadComponent: () => import('./pages/workflows/workflows.component').then(m => m.WorkflowsComponent)
  },
  { 
    path: 'testing', 
    loadComponent: () => import('./pages/testing/testing.component').then(m => m.TestingComponent)
  },
  { 
    path: 'monitoring', 
    loadComponent: () => import('./pages/monitoring/monitoring.component').then(m => m.MonitoringComponent)
  },
  { path: '**', redirectTo: '/dashboard' }
];
