import { Injectable, signal } from '@angular/core';
import { interval, Subscription } from 'rxjs';

export interface VersionState {
  configType: string;
  configId: string;
  localVersion: number;
  serverVersion: number;
  hasUnsavedChanges: boolean;
  lastChecked: Date;
}

@Injectable({
  providedIn: 'root'
})
export class ConfigVersionService {
  private versionStates = signal<Map<string, VersionState>>(new Map());
  private autoRefreshSubscription?: Subscription;
  private autoRefreshEnabled = signal(false);
  private autoRefreshInterval = 30000; // 30 seconds

  getVersionState(configType: string, configId: string): VersionState | undefined {
    const key = `${configType}:${configId}`;
    return this.versionStates().get(key);
  }

  setVersionState(state: VersionState): void {
    const key = `${state.configType}:${state.configId}`;
    const currentStates = new Map(this.versionStates());
    currentStates.set(key, state);
    this.versionStates.set(currentStates);
  }

  updateLocalVersion(configType: string, configId: string, version: number): void {
    const state = this.getVersionState(configType, configId);
    if (state) {
      this.setVersionState({
        ...state,
        localVersion: version,
        hasUnsavedChanges: false,
        lastChecked: new Date()
      });
    }
  }

  updateServerVersion(configType: string, configId: string, version: number): void {
    const state = this.getVersionState(configType, configId);
    if (state) {
      this.setVersionState({
        ...state,
        serverVersion: version,
        lastChecked: new Date()
      });
    } else {
      this.setVersionState({
        configType,
        configId,
        localVersion: version,
        serverVersion: version,
        hasUnsavedChanges: false,
        lastChecked: new Date()
      });
    }
  }

  markAsModified(configType: string, configId: string): void {
    const state = this.getVersionState(configType, configId);
    if (state) {
      this.setVersionState({
        ...state,
        hasUnsavedChanges: true
      });
    }
  }

  hasVersionConflict(configType: string, configId: string): boolean {
    const state = this.getVersionState(configType, configId);
    return state ? state.localVersion < state.serverVersion : false;
  }

  hasUnsavedChanges(configType: string, configId: string): boolean {
    const state = this.getVersionState(configType, configId);
    return state ? state.hasUnsavedChanges : false;
  }

  clearState(configType: string, configId: string): void {
    const key = `${configType}:${configId}`;
    const currentStates = new Map(this.versionStates());
    currentStates.delete(key);
    this.versionStates.set(currentStates);
  }

  enableAutoRefresh(callback: () => void): void {
    if (this.autoRefreshSubscription) {
      this.autoRefreshSubscription.unsubscribe();
    }

    this.autoRefreshEnabled.set(true);
    this.autoRefreshSubscription = interval(this.autoRefreshInterval).subscribe(() => {
      callback();
    });
  }

  disableAutoRefresh(): void {
    if (this.autoRefreshSubscription) {
      this.autoRefreshSubscription.unsubscribe();
      this.autoRefreshSubscription = undefined;
    }
    this.autoRefreshEnabled.set(false);
  }

  isAutoRefreshEnabled(): boolean {
    return this.autoRefreshEnabled();
  }

  setAutoRefreshInterval(milliseconds: number): void {
    this.autoRefreshInterval = milliseconds;
    // Restart auto-refresh if it's currently enabled
    if (this.autoRefreshEnabled()) {
      const callback = () => {}; // Will be set by the component
      this.disableAutoRefresh();
      this.enableAutoRefresh(callback);
    }
  }
}
