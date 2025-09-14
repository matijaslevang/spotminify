import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ContentService } from '../../content.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

@Component({
  selector: 'app-create-artist',
  templateUrl: './create-artist.component.html',
  styleUrls: ['./create-artist.component.css']
})
export class CreateArtistComponent {
  formGroup: FormGroup;
  error: string | null = null;
  selectedFile: File | null = null;
  imageError: string | null = null;
  uploadedFileName: string | null = null;

  availableGenres: string[] = [
    'Pop', 'Rock', 'Jazz', 'Hip-Hop', 'Classical', 'Electronic'
  ];

  constructor(private fb: FormBuilder, private contentService: ContentService, private snackBar: MatSnackBar, private router: Router) {
    this.formGroup = this.fb.group({
      name: ['', Validators.required],
      image: [null, Validators.required],
      biography: ['', Validators.required],
      genres: [[], Validators.required]
    });
  }

    onDragOver(event: DragEvent) {
    event.preventDefault();
  }

 onDrop(event: DragEvent) {
  event.preventDefault();
  if (event.dataTransfer?.files.length) {
    const file = event.dataTransfer.files[0];
    this.handleFile(file);
  }
}

onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length) {
    const file = input.files[0];
    this.handleFile(file);
  }
}

private handleFile(file: File) {
  if (!file.type.startsWith('image/')) {
    this.imageError = 'Only image files are allowed';
    this.selectedFile = null;
    this.formGroup.get('image')?.setValue(null);
    this.uploadedFileName = null;
    return;
  }

  this.selectedFile = file;
  this.uploadedFileName = file.name;
  this.imageError = null;
  this.formGroup.get('image')?.setValue(file);
}
  createArtist() {
    if (!this.selectedFile) {
      this.imageError = "Artist image must be selected";
      return;
    }

    if (this.formGroup.invalid) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const base64String = (reader.result as string).split(",")[1];

      const payload = {
        name: this.formGroup.get('name')?.value,
        biography: this.formGroup.get('biography')?.value,
        genres: this.formGroup.get('genres')?.value,
        image: base64String,
        imageType: this.selectedFile!.type.split("/")[1]
      };

      this.contentService.createArtist(payload).subscribe({
      next: (res: any) => {
        console.log('Artist created:', res);
        this.snackBar.open('Artist created successfully!', 'Close', {
          duration: 3000
        });
        this.formGroup.reset();
        this.selectedFile = null;
        this.uploadedFileName = null;
        this.router.navigate(['/home']);
      },
      error: (err) => {
        console.error('Error creating artist:', err);
        const message = err?.error?.error || 'Failed to create artist';
        this.snackBar.open(message, 'Close', {
          duration: 5000
        });
      }
    });
    };

    reader.readAsDataURL(this.selectedFile);
  }
}