import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

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

  constructor(private fb: FormBuilder) {
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

    const formData = new FormData();
    formData.append('name', this.formGroup.get('name')?.value);
    formData.append('biography', this.formGroup.get('biography')?.value);
    formData.append('genres', JSON.stringify(this.formGroup.get('genres')?.value));
    formData.append('image', this.selectedFile!);
    
    (formData as any).forEach((value: any, key: string) => {
      console.log(key, ':', value);
    });
  }
}
