import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { ContentService } from '../../content.service';
import { FormBuilder, Validators, FormControl, FormGroup, ReactiveFormsModule  } from '@angular/forms';
import { Genre } from '../../models/model';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-update-artist',
  templateUrl: './update-artist.component.html',
  styleUrls: ['./update-artist.component.css'] 
})

export class UpdateArtistComponent implements OnInit {
  file?: File;
  form: FormGroup;
  selectedFile: File | null = null;
  imageError: string | null = null;
  uploadedFileName: string | null = null;

  availableGenres: Genre[] = [];

  ngOnInit(): void {
    this.loadGenres();
  }

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    private snackBar: MatSnackBar,
    public ref: MatDialogRef<UpdateArtistComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { artist: any; availableGenres: any[] }
  ) {
    this.form = this.fb.group({
      name: ['', Validators.required],
      image: [null, Validators.required],
      biography: ['', Validators.required],
      genres: [[], Validators.required] // (number|string)[]
    });

    const a = data.artist ?? {};
    this.form.patchValue({
      name: a.name ?? '',
      biography: a.bio ?? a.biography ?? ''
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
  loadGenres(): void {
   this.api.getGenres().subscribe({
     next: (genres) => {
     this.availableGenres = genres;
        
       const a = this.data.artist ?? {};
        // 1. Dobijamo listu imena žanrova koje umetnik ima (npr. ['Rock', 'Hip-Hop'])
        const artistGenreNames: string[] = a.genres ?? [];
        const selectedGenreIdsWithNulls: (number | string | null)[] = artistGenreNames
        .map(name => {
            // Pronađi ceo Genre objekat iz availableGenres na osnovu imena
            const genre = this.availableGenres.find(g => g.genreName === name);
            // Vrati genreId ili null ako nije pronađen
            return genre ? genre.genreId : null;
        });
            
        // 3. Filtriramo null vrednosti. Koristimo jednostavan filter koji radi ispravno.
        const selectedGenreIds = selectedGenreIdsWithNulls.filter(id => id !== null) as (number | string)[];

        // 3. Patchujemo formu sa nizom ID-eva
       this.form.get('genres')?.patchValue(selectedGenreIds);

       console.log(this.availableGenres);
     },
     error: (err) => {
     this.snackBar.open('Failed to load genres. Please try again later.', 'Close', {
       duration: 5000,
         panelClass: ['error-snackbar']
       });
     }
     });
   }
  onCancel(): void {
    this.ref.close(false);
  }
}