import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { ContentService } from '../../content.service';
import { FormBuilder, Validators, FormControl, FormGroup, ReactiveFormsModule  } from '@angular/forms';

@Component({
  selector: 'app-update-artist',
  templateUrl: './update-artist.component.html',
  styleUrls: ['./update-artist.component.css'] 
})

export class UpdateArtistComponent {
  file?: File;
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    public ref: MatDialogRef<UpdateArtistComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { artist: any; availableGenres: any[] }
  ) {
    this.form = this.fb.group({
      name: ['', Validators.required],
      biography: ['', Validators.required],
      genres: [[], Validators.required] // (number|string)[]
    });

    const a = data.artist ?? {};
    this.form.patchValue({
      name: a.name ?? '',
      biography: a.bio ?? a.biography ?? '',
      genres: a.genresIds ?? a.genres ?? []
    });
  }

  onFile(e: Event): void {
    const input = e.target as HTMLInputElement;
    const f = input.files?.[0];
    if (f) this.file = f;
  }

  save(): void {
    if (this.form.invalid) return;

    const fd = new FormData();
    fd.append('artistId', String(this.data.artist.artistId ?? this.data.artist.id));
    fd.append('name', this.form.get('name')!.value);
    fd.append('biography', this.form.get('biography')!.value);

    const genres = (this.form.get('genres')!.value as (number | string)[]) ?? [];
    for (const g of genres) fd.append('genres', String(g));

    if (this.file) fd.append('image', this.file);

    this.api.updateArtist(fd).subscribe({
      next: () => this.ref.close(true),
      error: () => this.ref.close(false)
    });
  }

  onCancel(): void {
    this.ref.close(false);
  }
}