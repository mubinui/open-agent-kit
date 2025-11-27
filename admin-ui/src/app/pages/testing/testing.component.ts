import { Component, OnInit, signal, inject, effect, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';
import { ApiService, Message } from '../../services/api.service';
import { WorkflowConfig } from '../../models/workflow.model';
import { MarkdownPipe } from '../../pipes/markdown.pipe';

@Component({
  selector: 'app-testing',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatExpansionModule,
    MarkdownPipe
  ],
  templateUrl: './testing.component.html',
  styleUrl: './testing.component.scss'
})
export class TestingComponent implements OnInit {
  private apiService = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  workflows = signal<WorkflowConfig[]>([]);
  selectedWorkflowId = signal<string>('');
  sessionId = signal<string | null>(null);
  messages = signal<Message[]>([]);
  userMessage = signal('');
  loading = signal(false);
  sending = signal(false);

  @ViewChild('chatContainer') private chatContainer!: ElementRef;

  constructor() {
    effect(() => {
      // Track messages change
      this.messages();
      
      // Scroll to bottom after view updates
      setTimeout(() => {
        this.scrollToBottom();
      }, 100);
    });
  }

  private scrollToBottom(): void {
    try {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      }
    } catch (err) {
      console.error('Scroll to bottom failed', err);
    }
  }

  ngOnInit(): void {
    this.loadWorkflows();
  }

  loadWorkflows(): void {
    this.apiService.getWorkflows().subscribe({
      next: (data) => {
        this.workflows.set(data);
      },
      error: (err) => {
        this.snackBar.open('Failed to load workflows', 'Close', { duration: 3000 });
        console.error('Error loading workflows:', err);
      }
    });
  }

  startSession(): void {
    if (!this.selectedWorkflowId()) {
      this.snackBar.open('Please select a workflow', 'Close', { duration: 3000 });
      return;
    }

    this.loading.set(true);
    this.apiService.createSession(this.selectedWorkflowId()).subscribe({
      next: (session) => {
        this.sessionId.set(session.session_id);
        this.messages.set([]);
        this.loading.set(false);
        this.snackBar.open('Session started', 'Close', { duration: 2000 });
      },
      error: (err) => {
        this.snackBar.open('Failed to start session', 'Close', { duration: 3000 });
        this.loading.set(false);
        console.error('Error starting session:', err);
      }
    });
  }

  endSession(): void {
    if (!this.sessionId()) return;

    this.apiService.deleteSession(this.sessionId()!).subscribe({
      next: () => {
        this.sessionId.set(null);
        this.messages.set([]);
        this.snackBar.open('Session ended', 'Close', { duration: 2000 });
      },
      error: (err) => {
        this.snackBar.open('Failed to end session', 'Close', { duration: 3000 });
        console.error('Error ending session:', err);
      }
    });
  }

  sendMessage(): void {
    if (!this.sessionId() || !this.userMessage().trim()) return;

    const message = this.userMessage().trim();
    this.sending.set(true);

    // Add user message to chat
    this.messages.update(msgs => [...msgs, {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }]);

    this.apiService.sendMessage(this.sessionId()!, message).subscribe({
      next: (result) => {
        // Add assistant response to chat
        this.messages.update(msgs => [...msgs, {
          role: 'assistant',
          content: result.response,
          timestamp: new Date().toISOString()
        }]);
        
        this.userMessage.set('');
        this.sending.set(false);
      },
      error: (err) => {
        this.snackBar.open('Failed to send message', 'Close', { duration: 3000 });
        this.sending.set(false);
        console.error('Error sending message:', err);
      }
    });
  }

  clearChat(): void {
    this.messages.set([]);
  }

  onEnterKey(event: KeyboardEvent): void {
    if (!event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
