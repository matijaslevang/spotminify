import { Component, EventEmitter, Input, Output, TemplateRef, ViewChild } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-rate-content',
  templateUrl: './rate-content.component.html',
  styleUrls: ['./rate-content.component.css'] 
})
export class RateContentComponent {
  @Input() contentId!: number | string;              // obavezno
  @Input() contentType!: 'ALBUM' | 'SONG'| 'ARTIST';           // obavezno
  @Input() buttonLabel = 'Rate content';             // opcionalno
  @Output() rated = new EventEmitter<number>();

  @ViewChild('dialogTpl') dialogTpl!: TemplateRef<any>;
  rating = 0;
  submitting = false;

  constructor(private dialog: MatDialog, private http: HttpClient) {}

  open() { this.rating = 0; this.dialog.open(this.dialogTpl, { panelClass: 'mini-rate-dialog' }); }

  submit(d: any) {
    if (!this.rating) return;
    this.submitting = true;
    // TODO: prilagodi endpoint tvom beku
    const url = `/api/ratings`;
    const body = { targetId: this.contentId, targetType: this.contentType, value: this.rating };

    this.http.post(url, body).subscribe({
      next: () => { this.submitting = false; this.rated.emit(this.rating); d.close(); },
      error: () => { this.submitting = false; /* po želji prikaži toast */ }
    });
  }
}

