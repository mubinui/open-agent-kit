import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet, 
    RouterLink, 
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  title = 'Agent Builder';
  
  menuItems = [
    { path: '/dashboard', icon: 'dashboard', label: 'Dashboard' },
    { path: '/agents', icon: 'support_agent', label: 'Agents' },
    { path: '/tools', icon: 'build', label: 'Tools' },
    { path: '/workflows', icon: 'account_tree', label: 'Workflows' },
    { path: '/vector-db', icon: 'cloud', label: 'RAG Service' },
    { path: '/testing', icon: 'chat', label: 'Testing' },
    { path: '/monitoring', icon: 'monitoring', label: 'Monitoring' }
  ];
}
