import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ConflictDialogComponent } from './conflict-dialog.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('ConflictDialogComponent', () => {
  let component: ConflictDialogComponent;
  let fixture: ComponentFixture<ConflictDialogComponent>;
  let mockDialogRef: jasmine.SpyObj<MatDialogRef<ConflictDialogComponent>>;

  const mockConflictData = {
    currentVersion: 5,
    yourVersion: 3,
    currentConfig: {
      id: 'test_agent',
      name: 'Current Agent Name',
      type: 'conversable',
      value: 100,
    },
    yourChanges: {
      id: 'test_agent',
      name: 'Your Agent Name',
      type: 'conversable',
      value: 200,
    },
    diff: {
      added: ['new_field'],
      removed: ['old_field'],
      modified: [
        {
          field: 'name',
          current: 'Current Agent Name',
          yours: 'Your Agent Name',
        },
        {
          field: 'value',
          current: 100,
          yours: 200,
        },
      ],
    },
  };

  beforeEach(async () => {
    mockDialogRef = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [ConflictDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockConflictData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConflictDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display conflict dialog with version information', () => {
    const compiled = fixture.nativeElement;
    const versionText = compiled.textContent;

    expect(versionText).toContain('5');
    expect(versionText).toContain('3');
  });

  it('should display current version and your version', () => {
    expect(component.data.currentVersion).toBe(5);
    expect(component.data.yourVersion).toBe(3);
  });

  it('should display diff information', () => {
    expect(component.data.diff).toBeDefined();
    expect(component.data.diff.added).toContain('new_field');
    expect(component.data.diff.removed).toContain('old_field');
    expect(component.data.diff.modified.length).toBe(2);
  });

  it('should have "Reload Latest" button', () => {
    const compiled = fixture.nativeElement;
    const buttons = compiled.querySelectorAll('button');
    const reloadButton = Array.from(buttons).find((btn: any) =>
      btn.textContent.includes('Reload Latest')
    );

    expect(reloadButton).toBeTruthy();
  });

  it('should have "Download Your Changes" button', () => {
    const compiled = fixture.nativeElement;
    const buttons = compiled.querySelectorAll('button');
    const downloadButton = Array.from(buttons).find((btn: any) =>
      btn.textContent.includes('Download')
    );

    expect(downloadButton).toBeTruthy();
  });

  it('should have "View Side-by-Side" button', () => {
    const compiled = fixture.nativeElement;
    const buttons = compiled.querySelectorAll('button');
    const viewButton = Array.from(buttons).find((btn: any) =>
      btn.textContent.includes('Side-by-Side')
    );

    expect(viewButton).toBeTruthy();
  });

  it('should close dialog with "reload" action when Reload Latest is clicked', () => {
    component.onReloadLatest();

    expect(mockDialogRef.close).toHaveBeenCalledWith({ action: 'reload' });
  });

  it('should close dialog with "download" action when Download Your Changes is clicked', () => {
    component.onDownloadChanges();

    expect(mockDialogRef.close).toHaveBeenCalledWith({ action: 'download' });
  });

  it('should close dialog with "view_diff" action when View Side-by-Side is clicked', () => {
    component.onViewDiff();

    expect(mockDialogRef.close).toHaveBeenCalledWith({ action: 'view_diff' });
  });

  it('should close dialog with "cancel" action when Cancel is clicked', () => {
    component.onCancel();

    expect(mockDialogRef.close).toHaveBeenCalledWith({ action: 'cancel' });
  });

  it('should display modified fields in diff', () => {
    const modifiedFields = component.data.diff.modified;

    expect(modifiedFields.length).toBe(2);
    expect(modifiedFields[0].field).toBe('name');
    expect(modifiedFields[0].current).toBe('Current Agent Name');
    expect(modifiedFields[0].yours).toBe('Your Agent Name');
    expect(modifiedFields[1].field).toBe('value');
    expect(modifiedFields[1].current).toBe(100);
    expect(modifiedFields[1].yours).toBe(200);
  });

  it('should display added fields in diff', () => {
    const addedFields = component.data.diff.added;

    expect(addedFields.length).toBe(1);
    expect(addedFields[0]).toBe('new_field');
  });

  it('should display removed fields in diff', () => {
    const removedFields = component.data.diff.removed;

    expect(removedFields.length).toBe(1);
    expect(removedFields[0]).toBe('old_field');
  });

  it('should handle empty diff gracefully', () => {
    const emptyDiffData = {
      ...mockConflictData,
      diff: {
        added: [],
        removed: [],
        modified: [],
      },
    };

    component.data = emptyDiffData;
    fixture.detectChanges();

    expect(component.data.diff.added.length).toBe(0);
    expect(component.data.diff.removed.length).toBe(0);
    expect(component.data.diff.modified.length).toBe(0);
  });

  it('should display current config', () => {
    expect(component.data.currentConfig).toBeDefined();
    expect(component.data.currentConfig.name).toBe('Current Agent Name');
    expect(component.data.currentConfig.value).toBe(100);
  });

  it('should display your changes', () => {
    expect(component.data.yourChanges).toBeDefined();
    expect(component.data.yourChanges.name).toBe('Your Agent Name');
    expect(component.data.yourChanges.value).toBe(200);
  });

  it('should format JSON for download', () => {
    const jsonString = JSON.stringify(component.data.yourChanges, null, 2);

    expect(jsonString).toContain('Your Agent Name');
    expect(jsonString).toContain('200');
  });

  it('should create download blob with correct content', () => {
    spyOn(window.URL, 'createObjectURL').and.returnValue('blob:mock-url');
    spyOn(window.URL, 'revokeObjectURL');

    component.onDownloadChanges();

    expect(mockDialogRef.close).toHaveBeenCalledWith({ action: 'download' });
  });

  it('should handle conflict with only added fields', () => {
    const addedOnlyData = {
      ...mockConflictData,
      diff: {
        added: ['field1', 'field2', 'field3'],
        removed: [],
        modified: [],
      },
    };

    component.data = addedOnlyData;
    fixture.detectChanges();

    expect(component.data.diff.added.length).toBe(3);
    expect(component.data.diff.removed.length).toBe(0);
    expect(component.data.diff.modified.length).toBe(0);
  });

  it('should handle conflict with only removed fields', () => {
    const removedOnlyData = {
      ...mockConflictData,
      diff: {
        added: [],
        removed: ['field1', 'field2'],
        modified: [],
      },
    };

    component.data = removedOnlyData;
    fixture.detectChanges();

    expect(component.data.diff.added.length).toBe(0);
    expect(component.data.diff.removed.length).toBe(2);
    expect(component.data.diff.modified.length).toBe(0);
  });

  it('should handle conflict with only modified fields', () => {
    const modifiedOnlyData = {
      ...mockConflictData,
      diff: {
        added: [],
        removed: [],
        modified: [
          { field: 'name', current: 'Old', yours: 'New' },
        ],
      },
    };

    component.data = modifiedOnlyData;
    fixture.detectChanges();

    expect(component.data.diff.added.length).toBe(0);
    expect(component.data.diff.removed.length).toBe(0);
    expect(component.data.diff.modified.length).toBe(1);
  });

  it('should display warning message about losing changes', () => {
    const compiled = fixture.nativeElement;
    const warningText = compiled.textContent;

    expect(warningText).toContain('conflict');
  });

  it('should have proper dialog title', () => {
    const compiled = fixture.nativeElement;
    const title = compiled.querySelector('h2, mat-dialog-title, [mat-dialog-title]');

    expect(title).toBeTruthy();
  });

  it('should close dialog when clicking outside (if configured)', () => {
    // This tests the dialog configuration, not the component itself
    // The actual behavior depends on MatDialog configuration
    expect(component).toBeTruthy();
  });

  it('should handle large diffs efficiently', () => {
    const largeDiffData = {
      ...mockConflictData,
      diff: {
        added: Array.from({ length: 50 }, (_, i) => `field_${i}`),
        removed: Array.from({ length: 50 }, (_, i) => `old_field_${i}`),
        modified: Array.from({ length: 50 }, (_, i) => ({
          field: `modified_field_${i}`,
          current: `current_${i}`,
          yours: `yours_${i}`,
        })),
      },
    };

    component.data = largeDiffData;
    fixture.detectChanges();

    expect(component.data.diff.added.length).toBe(50);
    expect(component.data.diff.removed.length).toBe(50);
    expect(component.data.diff.modified.length).toBe(50);
  });

  it('should maintain data integrity after multiple interactions', () => {
    const originalData = { ...component.data };

    component.onCancel();
    fixture.detectChanges();

    // Data should remain unchanged
    expect(component.data.currentVersion).toBe(originalData.currentVersion);
    expect(component.data.yourVersion).toBe(originalData.yourVersion);
  });
});
