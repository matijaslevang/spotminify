import { Component, Inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ContentService } from '../../content.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Artist, Genre } from '../../models/model';
import { UploadService } from '../../../features/upload.service'; // Dodajte import za UploadService
import { firstValueFrom } from 'rxjs';
import { Song } from '../../models/model';

@Component({
  selector: 'app-update-album',
  templateUrl: './update-album.component.html',
  styleUrl: './update-album.component.css'
})
export class UpdateAlbumComponent implements OnInit {
  cover?: File;
  audioFile?: File;
  form: FormGroup;

  isSaving = false;
  availableArtists: Artist[] = [];
  availableGenres: Genre[] = [];
  albumSongs: Song[] = []; 
  songsLoading = false;
  ngOnInit(): void {
    this.loadGenres();
    this.loadArtists();
    this.loadAlbumSongs(this.data.album.id);
  }

  constructor(
    private fb: FormBuilder,
    private api: ContentService,
    private uploadService: UploadService,
    private snackBar: MatSnackBar,
    public ref: MatDialogRef<UpdateAlbumComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      album: any;                 
    }
  ){
    const a = data.album ?? {};
    this.form = this.fb.group({
      title: [a.title ?? '', Validators.required],
      genres: [[], Validators.required],
      artistIds: [a.artistsIds ?? [], Validators.required]
    });
  }
  loadAlbumSongs(albumId: string): void {
    this.songsLoading = true;
    this.api.getSongsByAlbum(albumId).subscribe({
      next: (songs) => {
        this.albumSongs = songs;
        this.songsLoading = false;
        console.log('Učitane pesme:', songs);
      },
      error: (err) => {
        console.error('Greška pri učitavanju pesama:', err);
        this.songsLoading = false;
        // Opcionalno: Prikazivanje poruke o grešci korisniku
      }
    });
  }
  onCover(e: Event){
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f) this.cover = f;
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
    let newImageKey: string | undefined = undefined;
    const albumId = this.data.album.albumId || this.data.album.id; // Dobijamo ID albuma

    try {
        // 1. RUKOVANJE COVER SLIKOM (Upload ako je izabrana nova)
        if (this.cover) {
            this.snackBar.open('Uploading cover image...', 'Dismiss', { duration: 0 });
            
            const imagePresigned = await firstValueFrom(
                this.uploadService.getPresignedUrl({
                    fileName: this.cover.name,
                    contentType: this.cover.type,
                    bucketType: 'image' as 'audio' | 'image'
                })
            );

            await this.uploadService.putToS3(imagePresigned.url, this.cover, this.cover.type);
            newImageKey = imagePresigned.key; // Ovo šaljemo Lambdi
        }

        this.snackBar.dismiss();
        this.snackBar.open('Updating album metadata...', 'Dismiss', { duration: 0 });

        // 2. PRIPREMA JSON PAYLOAD-a
        const artistIds: string[] = this.form.get('artistIds')!.value;
        const genreIds: (string|number)[] = this.form.get('genres')!.value; 

        const payload = {
            title: this.form.get('title')!.value,
            genres: this.getGenreNames(genreIds), 
            artistIds: artistIds,
            artistNames: this.getArtistNames(artistIds), 
            
            ...(newImageKey && { coverKey: newImageKey }),
        }; 

        this.api.updateAlbum(albumId, payload).subscribe({
            next: () => {
                this.snackBar.open('Album updated successfully!', 'Close', { duration: 3000 });
                this.ref.close(true);
            },
            error: (e) => {
                this.snackBar.open(e?.error?.error || e?.message || 'Failed to update album metadata.', 'Close', { duration: 5000, panelClass: ['error-snackbar'] });
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
        
      const s = this.data.album ?? {}; // Promenjeno a u s
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

      const s = this.data.album ?? {};
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