import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ContentService } from '../content.service';

@Component({
  selector: 'app-transcript-dialog',
  templateUrl: './transcript-dialog.component.html',
  styleUrl: './transcript-dialog.component.css'
})
export class TranscriptDialogComponent {

  transcription: string = ""

  constructor(
    private contentService: ContentService,
    public ref: MatDialogRef<TranscriptDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { singleId: string }
  ) {
    this.contentService.getTranscription(data.singleId).subscribe({
      next: (response: any) => {
        console.log(response)
        this.transcription = response.transcription
      }
    })
  }
}
