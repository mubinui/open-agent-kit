import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { ToolConfig } from '../../models/tool.model';

@Component({
  selector: 'app-tool-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCheckboxModule,
    MatSelectModule
  ],
  template: `
    <h2 mat-dialog-title>{{ isEdit() ? 'Edit Tool' : 'Register Tool' }}</h2>
    <mat-dialog-content>
      <form>
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>ID</mat-label>
          <input matInput [(ngModel)]="tool.id" name="id" required [disabled]="isEdit()">
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Name</mat-label>
          <input matInput [(ngModel)]="tool.name" name="name" required>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Description</mat-label>
          <textarea matInput [(ngModel)]="tool.description" name="description" rows="3" required></textarea>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Tool Type</mat-label>
          <mat-select [(ngModel)]="tool.type" name="type" required (selectionChange)="onToolTypeChange()">
            <mat-option value="function">Function Tool</mat-option>
            <mat-option value="api">API Tool</mat-option>
          </mat-select>
        </mat-form-field>

        @if (tool.type === 'function') {
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Entrypoint</mat-label>
            <input matInput [(ngModel)]="tool.entrypoint" name="entrypoint" required>
            <mat-hint>e.g., src.tools.calculator:calculate</mat-hint>
          </mat-form-field>
        }

        @if (tool.type === 'api') {
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>API URL</mat-label>
            <input matInput [(ngModel)]="tool.api_url" name="api_url" required>
            <mat-hint>e.g., https://api.example.com/v1/endpoint</mat-hint>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>HTTP Method</mat-label>
            <mat-select [(ngModel)]="tool.http_method" name="http_method" required>
              <mat-option value="GET">GET</mat-option>
              <mat-option value="POST">POST</mat-option>
              <mat-option value="PUT">PUT</mat-option>
              <mat-option value="DELETE">DELETE</mat-option>
              <mat-option value="PATCH">PATCH</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Authentication Type</mat-label>
            <mat-select [(ngModel)]="tool.auth_type" name="auth_type" required>
              <mat-option value="none">None</mat-option>
              <mat-option value="bearer">Bearer Token</mat-option>
              <mat-option value="api_key">API Key</mat-option>
              <mat-option value="basic">Basic Auth</mat-option>
            </mat-select>
          </mat-form-field>

          @if (tool.auth_type === 'api_key') {
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Auth Header Name</mat-label>
              <input matInput [(ngModel)]="tool.auth_header" name="auth_header" required>
              <mat-hint>e.g., X-API-Key or Authorization</mat-hint>
            </mat-form-field>
          }

          @if (tool.auth_type && tool.auth_type !== 'none') {
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Auth Environment Variable</mat-label>
              <input matInput [(ngModel)]="tool.auth_env_var" name="auth_env_var" required>
              <mat-hint>e.g., MY_API_KEY</mat-hint>
            </mat-form-field>
          }

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Request Headers (JSON)</mat-label>
            <textarea matInput [(ngModel)]="headersJson" name="headers" rows="3" (blur)="parseHeaders()"></textarea>
            <mat-hint>e.g., {{"{"}} "Content-Type": "application/json" {{"}"}}</mat-hint>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Request Body Template</mat-label>
            <textarea matInput [(ngModel)]="tool.body_template" name="body_template" rows="4"></textarea>
            <mat-hint>Use {{"{input}"}} for variables. e.g., {{"{"}} "query": "{{"{input}"}}" {{"}"}}</mat-hint>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Response Path</mat-label>
            <input matInput [(ngModel)]="tool.response_path" name="response_path">
            <mat-hint>JSON path to extract result, e.g., data.result</mat-hint>
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Timeout (seconds)</mat-label>
            <input matInput type="number" [(ngModel)]="tool.timeout" name="timeout" min="1" max="300">
            <mat-hint>Request timeout in seconds (default: 30)</mat-hint>
          </mat-form-field>

          <div class="checkbox-field">
            <mat-checkbox [(ngModel)]="tool.forward_user_context" name="forward_user_context">
              Forward User Context Headers
            </mat-checkbox>
          </div>

          @if (tool.forward_user_context) {
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Client Username (x-client-username)</mat-label>
              <input matInput [(ngModel)]="tool.client_username" name="client_username">
              <mat-hint>Username to send in x-client-username header (leave empty to use from JWT)</mat-hint>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Client Roles (x-client-ref)</mat-label>
              <input matInput [(ngModel)]="tool.client_roles" name="client_roles">
              <mat-hint>Comma-separated roles for x-client-ref header (leave empty to use from JWT)</mat-hint>
            </mat-form-field>
          }
        }

        <div class="checkbox-field">
          <mat-checkbox [(ngModel)]="tool.enabled" name="enabled">Enabled</mat-checkbox>
        </div>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancel</button>
      <button mat-raised-button color="primary" (click)="onSave()">Save</button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host {
      display: block;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 1.25rem;
      font-weight: 600;
      // Color handled by global styles
    }

    mat-dialog-content {
      width: 100%;
      padding: 20px 24px;
      box-sizing: border-box;
      overflow-x: auto;
      overflow-y: auto;
      flex: 1;
      
      &::-webkit-scrollbar {
        width: 12px;
        height: 12px;
      }
      
      &::-webkit-scrollbar-track {
        background: #e2e8f0;
        border-radius: 6px;
      }
      
      &::-webkit-scrollbar-thumb {
        background: #94a3b8;
        border-radius: 6px;
        border: 3px solid #e2e8f0;
        
        &:hover {
          background: #64748b;
        }
      }
    }

    .full-width {
      width: 100%;
      margin-bottom: 12px;
      box-sizing: border-box;
    }
    .checkbox-field {
      margin-bottom: 12px;
    }

    form {
      display: flex;
      flex-direction: column;
      width: 100%;
      padding-top: 4px;
    }
  `]
})
export class ToolFormDialogComponent {
  private dialogRef = inject(MatDialogRef<ToolFormDialogComponent>);
  private data = inject(MAT_DIALOG_DATA);

  tool: ToolConfig;
  isEdit = signal(false);
  headersJson: string = '';

  constructor() {
    if (this.data.tool) {
      this.tool = { ...this.data.tool };
      this.isEdit.set(true);
      
      // Map settings to top-level properties for API tools
      if (this.tool.settings && this.tool.settings['type'] === 'api') {
        this.tool.type = 'api';
        this.tool.api_url = this.tool.settings['api_url'];
        this.tool.http_method = this.tool.settings['http_method'];
        this.tool.auth_type = this.tool.settings['auth_type'];
        this.tool.auth_header = this.tool.settings['auth_header'];
        this.tool.auth_env_var = this.tool.settings['auth_env_var'];
        this.tool.headers = this.tool.settings['headers'];
        this.tool.body_template = this.tool.settings['body_template'];
        this.tool.response_path = this.tool.settings['response_path'];
        this.tool.timeout = this.tool.settings['timeout'];
        this.tool.forward_user_context = this.tool.settings['forward_user_context'];
        this.tool.client_username = this.tool.settings['client_username'];
        this.tool.client_roles = this.tool.settings['client_roles'];
      } else {
        this.tool.type = 'function';
      }

      // Convert headers object to JSON string for editing
      if (this.tool.headers) {
        this.headersJson = JSON.stringify(this.tool.headers, null, 2);
      }
    } else {
      this.tool = {
        id: '',
        name: '',
        description: '',
        type: 'function',
        entrypoint: '',
        enabled: true,
        http_method: 'POST',
        auth_type: 'none',
        timeout: 30
      };
    }
  }

  onToolTypeChange(): void {
    // Clear type-specific fields when switching types
    if (this.tool.type === 'function') {
      delete this.tool.api_url;
      delete this.tool.http_method;
      delete this.tool.headers;
      delete this.tool.auth_type;
      delete this.tool.auth_header;
      delete this.tool.auth_env_var;
      delete this.tool.body_template;
      delete this.tool.response_path;
      delete this.tool.timeout;
      delete this.tool.forward_user_context;
      delete this.tool.client_username;
      delete this.tool.client_roles;
      this.headersJson = '';
    } else if (this.tool.type === 'api') {
      delete this.tool.entrypoint;
      this.tool.http_method = 'POST';
      this.tool.auth_type = 'none';
      this.tool.timeout = 30;
      this.tool.forward_user_context = true; // Default to true for convenience
    }
  }

  parseHeaders(): void {
    if (this.headersJson.trim()) {
      try {
        this.tool.headers = JSON.parse(this.headersJson);
      } catch (e) {
        console.error('Invalid JSON for headers:', e);
      }
    } else {
      delete this.tool.headers;
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    // Parse headers before saving
    this.parseHeaders();
    
    // Store API configuration in settings field for backend compatibility
    if (this.tool.type === 'api') {
      this.tool.settings = {
        type: 'api',
        api_url: this.tool.api_url,
        http_method: this.tool.http_method,
        auth_type: this.tool.auth_type,
        auth_header: this.tool.auth_header,
        auth_env_var: this.tool.auth_env_var,
        headers: this.tool.headers,
        body_template: this.tool.body_template,
        response_path: this.tool.response_path,
        timeout: this.tool.timeout,
        forward_user_context: this.tool.forward_user_context,
        client_username: this.tool.client_username,
        client_roles: this.tool.client_roles
      };
    }
    
    this.dialogRef.close(this.tool);
  }
}
