import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ContentService } from '../../content.service';
import { MatSlideToggle } from '@angular/material/slide-toggle';
import { Genre, Artist } from '../../models/model';
import { MatSnackBar } from '@angular/material/snack-bar';
@Component({
  selector: 'app-update-song',
  templateUrl: './update-song.component.html',
  styleUrl: './update-song.component.css'
})
export class UpdateSongComponent implements OnInit{
  file?: File;              
  audioFile?: File; 
  form: FormGroup;
  availableArtists: Artist[] = [];
  availableGenres: Genre[] = [];

  ngOnInit(): void {
    this.loadGenres();
    this.loadArtists();
  }

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    private snackBar: MatSnackBar,
    public ref: MatDialogRef<UpdateSongComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      single: any;           // očekuje { songId | id, name, genres[], artists[], explicit? }
      availableGenres: any[] // Pretpostavljeno: niz stringova
      artistOptions: string[];
    }
  ){
    const s = data.single ?? {};
    this.form = this.fb.group({
      title: [s.title ?? '', Validators.required],
      genres: [[], Validators.required],
      artistIds: [s.artistsIds ?? [], Validators.required],
      explicit: [!!s.explicit]
    });
    console.log(s)
  }

  onFile(e: Event){
    const input = e.target as HTMLInputElement;
    const f = input.files?.[0];
    if (f) this.file = f;
  }
  onAudioFile(e: Event): void {
   const input = e.target as HTMLInputElement;
   const f = input.files?.[0];
   if (f) this.audioFile = f;
  }

  save(){
    if (this.form.invalid) return;

    const fd = new FormData();
    fd.append('songId', String(this.data.single.songId ?? this.data.single.id));
    fd.append('title', this.form.get('title')!.value);
    for (const g of (this.form.get('genres')!.value as string[])) fd.append('genres', g);
    for (const a of (this.form.get('artistIds')!.value as string[])) fd.append('artistIds', a);
    fd.append('explicit', String(!!this.form.get('explicit')!.value));
    if (this.file) fd.append('image', this.file);

    // this.api.updateSingle(fd).subscribe({
    //   next: () => this.ref.close(true),
    //   error: () => this.ref.close(false)
    // });
  }
  loadGenres(): void {
    this.api.getGenres().subscribe({
      next: (genres) => {
      this.availableGenres = genres;
        
      const s = this.data.single ?? {}; // Promenjeno a u s
       // 1. Dobijamo listu imena žanrova koje pesma ima
       const songGenreNames: string[] = s.genres ?? []; // Promenjeno artistGenreNames u songGenreNames

      // 2. Mapiramo imena u ID-eve
         const selectedGenreIdsWithNulls: (number | string | null)[] = songGenreNames
         .map(name => {
         // Pronađi ceo Genre objekat iz availableGenres na osnovu imena
         const genre = this.availableGenres.find(g => g.genreName === name);
         // Vrati genreId ili null ako nije pronađen
         return genre ? genre.genreId : null;
       });

         // 3. Filtriramo null vrednosti. 
       const selectedGenreIds = selectedGenreIdsWithNulls.filter(id => id !== null) as (number | string)[];

         // 4. Patchujemo formu sa nizom ID-eva
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
  loadArtists(): void {
  this.api.getArtists().subscribe({
    next: (artists) => {
      this.availableArtists = artists;
    },
    error: (err) => {
      this.snackBar.open('Failed to load artists. Please try again later.', 'Close', {
        duration: 5000,
        panelClass: ['error-snackbar']
      });
    }
  });
  }
  cancel(){ this.ref.close(false); }
}