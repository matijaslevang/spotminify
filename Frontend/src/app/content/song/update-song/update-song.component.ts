import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ContentService } from '../../content.service';
import { MatSlideToggle } from '@angular/material/slide-toggle';
import { Genre, Artist } from '../../models/model';
import { UploadService } from '../../../features/upload.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs'; // DODATO: Uvozimo firstValueFrom za asinhrono rešavanje Observable-a

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
  isSaving = false; 
  
  ngOnInit(): void {
    this.loadGenres();
    this.loadArtists();
  }

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    private snackBar: MatSnackBar,
    private uploadService: UploadService,
    public ref: MatDialogRef<UpdateSongComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      single: any;           // očekuje { songId | id, name, genres[], artists[], explicit? }
      availableGenres: any[] // Pretpostavljeno: niz stringova
      selectedAritsts: string[];
    }
  ){
    const s = data.single ?? {};
    this.form = this.fb.group({
      title: [s.title ?? '', Validators.required],
      genres: [[], Validators.required],
      artistIds: [s.artistsIds ?? [], Validators.required],
      //explicit: [!!s.explicit]
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

  getGenreNames(genreIds: (string | number)[]): string[] {
     return genreIds
       .map(id => this.availableGenres.find(g => g.genreId === id)?.genreName)
       .filter((name): name is string => !!name);
  }

  getArtistNames(artistIds: string[]): string[] {
   return artistIds
     .map(id => this.availableArtists.find(a => a.artistId === id)?.name)
     .filter((name): name is string => !!name);
  }
   async save(){
     if (this.form.invalid || this.isSaving) return;

     this.isSaving = true;
     let newAudioKey: string | undefined = undefined;
     let newImageKey: string | undefined = undefined;

   try {

   if (this.audioFile) {
     this.snackBar.open('Uploading audio file...', 'Dismiss', { duration: 0 });

      const audioPresigned = await firstValueFrom(
      this.uploadService.getPresignedUrl({
      fileName: this.audioFile.name,
      contentType: this.audioFile.type,
      bucketType: 'audio'})
      );

      await this.uploadService.putToS3(audioPresigned.url, this.audioFile, this.audioFile.type);
       newAudioKey = audioPresigned.key; // Ovo šaljemo Lambdi
     }


     if (this.file) {
       this.snackBar.open('Uploading image file...', 'Dismiss', { duration: 0 });
       const imagePresigned = await firstValueFrom(
         this.uploadService.getPresignedUrl({
           fileName: this.file.name,
           contentType: this.file.type,
           bucketType: 'image' as 'audio' | 'image'
         })
       );
         await this.uploadService.putToS3(imagePresigned.url, this.file, this.file.type);
         newImageKey = imagePresigned.key; // Ovo šaljemo Lambdi
     }

       this.snackBar.dismiss();
       this.snackBar.open('Updating single metadata...', 'Dismiss', { duration: 0 });

     const artistIds: string[] = this.form.get('artistIds')!.value;
     const genreIds: (string|number)[] = this.form.get('genres')!.value; // ID-evi iz mat-select-a

     const payload = {
       title: this.form.get('title')!.value,
       genres: this.getGenreNames(genreIds), // Lambda zahteva imena žanrova
       artistIds: artistIds,
       artistNames: this.getArtistNames(artistIds), // Lambda zahteva imena izvođača
       //explicit: !!this.form.get('explicit')!.value,
   
       // Novi S3 ključevi. Ako fajl nije zamenjen, ostaju nedefinisani i Lambda ih ignoriše
         ...(newAudioKey && { audioKey: newAudioKey }), 
         ...(newImageKey && { imageKey: newImageKey }),
   
     }; 
     const singleId = this.data.single.singleId;
     console.log(singleId)
     console.log('Single id')
     // 4. POZIV API-ja za ažuriranje metapodataka
       this.api.updateSingle(singleId, payload).subscribe({
   next: () => {
           this.snackBar.open('Single updated successfully!', 'Close', { duration: 3000 });
          
           this.ref.close(true);
     },
      error: (e) => {
        this.snackBar.open(e?.error?.error || e?.message || 'Failed to update single metadata.', 'Close', { duration: 5000, panelClass: ['error-snackbar'] });
        this.isSaving = false;
   }
     });

   } catch (e) {
       console.error('Upload or update failed:', e);
      this.snackBar.open('File upload failed. Try again.', 'Close', { duration: 5000, panelClass: ['error-snackbar'] });
      this.isSaving = false;
   }
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

      const s = this.data.single ?? {};
      const selectedArtistIds: string[] = s.artistIds ?? [];
      
      this.form.get('artistIds')?.patchValue(selectedArtistIds); 

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