import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators, FormGroup } from '@angular/forms';
import { UploadService } from '../upload.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Genre, Artist } from '../../content/models/model';
import { ContentService } from '../../content/content.service';

@Component({
  selector: 'app-admin',
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  // State
  isSubmittingSingle = false;
  isSubmittingAlbum = false;

  files: File[] = [];
  cover?: File;
  singleCover?: File;

  coverPreview?: string | ArrayBuffer | null;
  singleCoverPreview?: string | ArrayBuffer | null;

  tabIndex = 0; // 0 = single, 1 = album

  albumStep = 0;

  availableGenres: Genre[] = [];
  availableArtists: Artist[] = [];
  
  genreOptions: string[] = ['Pop', 'Rock', 'Hip-Hop', 'R&B', 'Electronic', 'House', 'Techno', 'Jazz', 'Classical', 'Folk', 'Indie', 'Metal'];

  // Dropdown za artiste - možeš učitavati dinamički sa API-ja ako treba
  artistOptions: { id: string, name: string }[] = [
    { id: '1', name: 'Artist A' },
    { id: '2', name: 'Artist B' },
    { id: '3', name: 'Artist C' }
  ];

  singleForm!: FormGroup;
  albumForm!: FormGroup;
  albumSingleForm!: FormGroup;

  // Kolekcija singlova za album
  albumSingles: Array<{ title: string; genres: string[]; artistIds: string[]; artistNames: string[]; fileIndex: number }> = [];

  constructor(private fb: FormBuilder, private api: UploadService, private contentService: ContentService,private snack: MatSnackBar) {}

  ngOnInit() {
    this.loadGenres();
    this.loadArtists();
    this.singleForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [[] as string[]],
      artistNames: [[] as string[]],
      explicit: [false]
    });

    this.albumForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [[] as string[]],
      artistNames: [[] as string[]],
    });

    this.albumSingleForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [[] as string[]],
      artistNames: [[] as string[]],
      fileIndex: [null, [Validators.required]]
    });
  }

  // Handleri za fajlove
  onFilesSelected(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (input.files) {
      this.addFiles(Array.from(input.files));
      input.value = ''; // Reset za ponovno biranje
    }
  }

  onDragOver(e: DragEvent) {
    e.preventDefault();
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer?.files) {
      this.addFiles(Array.from(e.dataTransfer.files));
    }
  }

  private addFiles(newFiles: File[]) {
    // Filtriraj samo audio fajlove
    const audioFiles = newFiles.filter(f => f.type.startsWith('audio/'));
    if (audioFiles.length < newFiles.length) {
      this.snack.open('Only audio files are accepted', 'Close', { duration: 3000 });
    }
    this.files = [...this.files, ...audioFiles];
  }

  remove(index: number) {
    this.files.splice(index, 1);
    // Ažuriraj fileIndex u albumSingles ako treba
    this.albumSingles = this.albumSingles.filter(s => s.fileIndex !== index)
      .map(s => ({ ...s, fileIndex: s.fileIndex > index ? s.fileIndex - 1 : s.fileIndex }));
  }

  // Handleri za cover
  onCoverSelected(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (input.files?.[0]) {
      this.setCover(input.files[0]);
      input.value = '';
    }
  }
  onSingleCoverSelected(ev: Event) {
  const input = ev.target as HTMLInputElement;
  if (input.files?.[0]) {
    this.setSingleCover(input.files[0]);
    input.value = '';
  }
}
  loadGenres(): void {
    this.contentService.getGenres().subscribe({
      next: (genres) => {
        this.availableGenres = genres;
      },
      error: (err) => {
        this.snack.open('Failed to load genres. Please try again later.', 'Close', {
          duration: 5000,
          panelClass: ['error-snackbar']
        });
      }
    });
  }
  loadArtists(): void {
    this.contentService.getArtists().subscribe({
      next: (artists) => {
        this.availableArtists = artists;
      },
      error: (err) => {
        this.snack.open('Failed to load artists. Please try again later.', 'Close', {
          duration: 5000,
          panelClass: ['error-snackbar']
        });
      }
    });
  }
  onCoverDrop(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer?.files?.[0]) {
      this.setCover(e.dataTransfer.files[0]);
    }
  }
  
  onSingleAlbumCoverDrop(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer?.files?.[0]) {
      this.setSingleCover(e.dataTransfer.files[0]);
    }
  }
  private setCover(file: File) {
    if (!file.type.startsWith('image/')) {
      this.snack.open('Only images are accepted for cover', 'Close', { duration: 3000 });
      return;
    }
    this.cover = file;
    const reader = new FileReader();
    reader.onload = () => this.coverPreview = reader.result;
    reader.readAsDataURL(file);
  }

  removeCover() {
    this.cover = undefined;
    this.coverPreview = null;
  }

  private setSingleCover(file: File) {
    if (!file.type.startsWith('image/')) {
      this.snack.open('Only images are accepted for cover', 'Close', { duration: 3000 });
      return;
    }
    this.singleCover = file;
    const reader = new FileReader();
    reader.onload = () => this.singleCoverPreview = reader.result;
    reader.readAsDataURL(file);
  }

  removeSingleCover() {
    this.singleCover = undefined;
    this.singleCoverPreview = null;
  }

  // Helper za B64
  private readAsB64(file: File): Promise<string> {
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res((r.result as string).split(',')[1]);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
  }

  renderArtistNames(ids: string[]): string {
    const map = new Map(this.artistOptions.map(a => [a.id, a.name]));
    return ids.map(id => map.get(id) || id).join(', ');
  }
  private mapArtistIdsToNames(artistIds: string[]): string[] {
    if (!this.availableArtists || !artistIds) return [];
    
    const nameMap = new Map(this.availableArtists.map(a => [a.artistId, a.name]));
    
    return artistIds
      .map(id => nameMap.get(id))
      .filter((name): name is string => !!name); // Filter null/undefined i TypeScript tip
  }
  // SINGLE SUBMIT
  async submitSingle() {
  if (this.singleForm.invalid || !this.files.length) {
    this.snack.open('Choose an audio file', 'Close', { panelClass: 'snack-error' });
    return;
  }
  this.isSubmittingSingle = true;
  try {
    const selectedArtistIds = this.singleForm.value.artistIds;
    const selectedArtistNames = this.mapArtistIdsToNames(selectedArtistIds);
    this.singleForm.get('artistNames')?.setValue(selectedArtistNames);

    const audioFile = this.files[0];
    const audioContentType = audioFile.type || 'audio/mpeg';
    // 1) presign audio
    const presA = await this.api.getPresignedUrl({
      bucketType: 'audio',
      fileName: audioFile.name,
      contentType: audioContentType
    }).toPromise();

    // 2) PUT na S3
    await this.api.putToS3(presA!.url, audioFile, audioContentType);

    // 3) presign cover (opciono)
    let imageKey: string | undefined;
    if (this.cover) {
      const presI = await this.api.getPresignedUrl({
        bucketType: 'image',
        fileName: this.cover.name,
        contentType: this.cover.type || 'image/jpeg'
      }).toPromise();
      await this.api.putToS3(presI!.url, this.cover, this.cover.type);
      imageKey = presI!.key;
    }

    // 4) POST /singles sa key-evima
    const payload = {
      title: this.singleForm.value.title,
      artistIds: this.singleForm.value.artistIds,
      genres: this.singleForm.value.genres,
      artistNames: this.singleForm.value.artistNames,
      explicit: !!this.singleForm.value.explicit,
      audioKey: presA!.key,
      ...(imageKey ? { imageKey } : {})
    };

    this.api.createSingle(payload).subscribe({
      next: () => {
        this.snack.open('Single created', 'OK', { duration: 2500 });
        this.resetSingle();
        this.files = []; this.cover = undefined; this.coverPreview = null;
      },
      error: (e) => this.snack.open(e?.error?.error || e?.error?.message || 'Failed', 'Close', { panelClass: 'snack-error' })
    });
  } catch {
    this.snack.open('Upload failed', 'Close', { panelClass: 'snack-error' });
  } finally {
    this.isSubmittingSingle = false;
  }
}

   goToSingles() { 
    // Popunjavanje albumForm sa imenima pre prelaska na sledeći korak
    // const selectedArtistIds = this.albumForm.value.artistIds;
    // const selectedArtistNames = this.mapArtistIdsToNames(selectedArtistIds);
    // this.albumForm.get('artistNames')?.setValue(selectedArtistNames);
    this.albumStep = 1; 
}
  backToAlbum() { this.albumStep = 0; }

  addAlbumSingle() {
    if (this.albumSingleForm.invalid) return;

    const selectedArtistIds = this.albumSingleForm.value.artistIds;
    const selectedArtistNames = this.mapArtistIdsToNames(selectedArtistIds);

    this.albumSingles.push({ 
          ...this.albumSingleForm.value,
          artistNames: selectedArtistNames // Dodato artistNames
      });
      
     this.albumSingleForm.reset({ title: '', genres: [], artistIds: [], artistNames: [], fileIndex: null });
    }
  // addAlbumSingle() {
  //   if (this.albumSingleForm.invalid) return;
  //   this.albumSingles.push({ ...this.albumSingleForm.value });
  //   this.albumSingleForm.reset({ title: '', genres: [], artistIds: [], fileIndex: null });
  // }
  removeAlbumSingle(i: number) { this.albumSingles.splice(i, 1); }

  // FINAL SAVE album
  async submitAlbumWizard() {
  if (!this.cover) {
    this.snack.open('Cover is required for album', 'Close', { panelClass: 'snack-error' });
    return;
  }
  if (!this.albumSingles.length) {
    this.snack.open('Add at least one single', 'Close', { panelClass: 'snack-error' });
    return;
  }
  const bad = this.albumSingles.find(s => s.fileIndex == null || !this.files[s.fileIndex]);
  if (bad) {
    this.snack.open('Each single must reference an audio file', 'Close', { panelClass: 'snack-error' });
    return;
  }

  this.isSubmittingAlbum = true;
  try {
    // 1) cover presign+PUT
    const presCover = await this.api.getPresignedUrl({
      bucketType: 'image',
      fileName: this.cover.name,
      contentType: this.cover.type || 'image/jpeg'
    }).toPromise();
    await this.api.putToS3(presCover!.url, this.cover, this.cover.type);
    const coverKey = presCover!.key;
    
    const selectedArtistIds = this.albumForm.value.artistIds;
    const selectedArtistNames = this.mapArtistIdsToNames(selectedArtistIds);
    this.albumForm.get('artistNames')?.setValue(selectedArtistNames);

    // 2) svaka traka presign+PUT
    const tracks = [];
    for (let i = 0; i < this.albumSingles.length; i++) {
      const s = this.albumSingles[i];
      const f = this.files[s.fileIndex];

      const presA = await this.api.getPresignedUrl({
        bucketType: 'audio',
        fileName: f.name,
        contentType: f.type || 'audio/mpeg'
      }).toPromise();
      await this.api.putToS3(presA!.url, f, f.type);

      let imageKey: string | undefined;
      if (this.singleCover) {
      const presB = await this.api.getPresignedUrl({
        bucketType: 'image',
        fileName: this.singleCover.name,
        contentType: this.singleCover.type || 'image/jpeg'
      }).toPromise();
      await this.api.putToS3(presB!.url, this.singleCover, this.singleCover.type);
      imageKey = presB!.key;
      }

      tracks.push({
        title: s.title,
        artistIds: s.artistIds,
        artistNames: s.artistNames,
        genres: s.genres,
        trackNo: i + 1,
        audioKey: presA!.key,
        ...(imageKey ? { imageKey } : {})
      });
    }

    // 3) POST /albums
    const payload = {
      title: this.albumForm.value.title,
      artistIds: this.albumForm.value.artistIds,
      artistNames: this.albumForm.value.artistNames,
      genres: this.albumForm.value.genres,
      coverKey,
      tracks
    };

    this.api.createAlbum(payload).subscribe({
      next: () => {
        this.snack.open('Album created', 'OK', { duration: 2500 });
        this.resetAlbum();
        this.albumStep = 0;
        this.albumSingles = [];
        this.files = []; this.cover = undefined; this.coverPreview = null;
      },
      error: e => this.snack.open(e?.error?.error || e?.error?.message || 'Album failed', 'Close', { panelClass: 'snack-error' })
    });
  } catch {
    this.snack.open('Upload failed', 'Close', { panelClass: 'snack-error' });
  } finally {
    this.isSubmittingAlbum = false;
  }
}
 resetSingle() {
   this.singleForm.reset({ title: '', genres: [], artistIds: [], artistNames: [], explicit: false });
   }

  resetAlbum() {
    // this.albumForm.reset({ title: '', genres: [], artistIds: [], artistNames: [] });
    //this.albumSingleForm.reset({ title: '', genres: [], artistIds: [], artistNames: [], fileIndex: null });
    this.albumSingles = [];
    this.albumStep = 0;
 }

} 